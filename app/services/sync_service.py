"""
Service for handling FPLog synchronization from fingerprint devices
Supports both ZK protocol and Fingerspot API devices
"""
import threading
import time
from datetime import datetime, timedelta
from flask import flash
from app.models.attendance import AttendanceModel
from config.config import Config
from config.devices import (
    FINGERPRINT_DEVICES,
    determine_status,
    get_status_display,
    get_device_display_name,
    get_zk_devices,
    get_fingerspot_api_devices,
    get_devices_by_connection_type
)
from app.services.online_attendance_service import OnlineAttendanceService

class SyncService:
    """Service for synchronizing FPLog data from multiple fingerprint devices"""
    
    def __init__(self):
        self.attendance_model = AttendanceModel()
        self.devices = FINGERPRINT_DEVICES
        self.sync_threads = {}
        self.sync_status = {}
        self._pyzk_available = self._check_pyzk_availability()
        
        # Initialize Online Attendance service
        try:
            self.online_attendance_service = OnlineAttendanceService()
            print("Online Attendance service initialized successfully")
        except Exception as e:
            self.online_attendance_service = None
            print(f"Warning: Online Attendance service not available - Initialization error: {e}")
        
        # Initialize Fingerspot API service
        try:
            from app.services.fingerspot_service import FingerspotAPIService
            self.fingerspot_service = FingerspotAPIService()
            print("Fingerspot API service initialized successfully")
        except ImportError as e:
            self.fingerspot_service = None
            print(f"Warning: Fingerspot service not available - Import error: {e}")
        except Exception as e:
            self.fingerspot_service = None
            print(f"Warning: Fingerspot service not available - Initialization error: {e}")
        
        # Initialize attendance_queues table
        self._initialize_attendance_queue_table()
        
    def _initialize_attendance_queue_table(self):
        """Initialize attendance_queues table if it doesn't exist"""
        try:
            success, message = self.attendance_model.create_attendance_queues_table()
            if success:
                print("Attendance queue table initialized successfully")
            else:
                print(f"Warning: Could not initialize attendance queue table: {message}")
        except Exception as e:
            print(f"Error initializing attendance queue table: {e}")
        
    def _check_pyzk_availability(self):
        """Check if pyzk module is available"""
        try:
            from zk import ZK
            return True
        except ImportError:
            print("Warning: pyzk module not available. Device sync functionality will be limited.")
            return False
    
    def _get_employee_attid_mapping(self):
        """Get PIN to ATTID mapping from employees table"""
        try:
            attid_mapping = {}
            conn = self.attendance_model.db_manager.get_sqlserver_connection()
            if not conn:
                print("Warning: Could not connect to SQL Server for employee mapping")
                return attid_mapping
            
            cursor = conn.cursor()
            cursor.execute("SELECT pin, attid FROM employees WHERE pin IS NOT NULL AND pin != '' AND attid IS NOT NULL")
            employee_data = cursor.fetchall()
            
            for row in employee_data:
                pin = str(row[0]).strip()
                attid = row[1]
                attid_mapping[pin] = attid
            
            cursor.close()
            conn.close()
            
            print(f"Loaded {len(attid_mapping)} PIN-to-ATTID mappings from employees table")
            return attid_mapping
            
        except Exception as e:
            print(f"Warning: Could not fetch employee ATTID mapping: {str(e)}")
            return {}
        
    def _get_device_config(self):
        """Get device configuration from config (deprecated - now using FINGERPRINT_DEVICES)"""
        return FINGERPRINT_DEVICES
    
    def sync_single_device(self, device_config, start_date=None, end_date=None):
        """Synchronize FPLog data from a single device (ZK or Fingerspot API)"""
        device_name = device_config['name']
        connection_type = device_config.get('connection_type', 'zk')
        
        # Initialize sync status with appropriate initial status based on connection type
        initial_status = 'reading' if connection_type == 'online_attendance' else 'connecting'
        initial_message = (
            'Reading attendance data from Online Attendance API...' 
            if connection_type == 'online_attendance' 
            else f'Connecting to {connection_type} device...'
        )
        
        self.sync_status[device_name] = {
            'status': initial_status,
            'message': initial_message,
            'start_time': datetime.now(),
            'records_synced': 0,
            'connection_type': connection_type
        }
        
        # Route to appropriate sync method based on connection type
        if connection_type == 'fingerspot_api':
            return self._sync_fingerspot_device(device_config, start_date, end_date)
        elif connection_type == 'online_attendance':
            return self._sync_online_attendance_device(device_config, start_date, end_date)
        else:
            return self._sync_zk_device(device_config, start_date, end_date)
    
    def _sync_zk_device(self, device_config, start_date=None, end_date=None):
        """Synchronize FPLog data from a ZK device"""
        device_name = device_config['name']
        
        if not self._pyzk_available:
            self.sync_status[device_name]['status'] = 'error'
            self.sync_status[device_name]['message'] = 'pyzk module not available. Please install: pip install pyzk'
            self.sync_status[device_name]['end_time'] = datetime.now()
            return False, 'pyzk module not available. Please install: pip install pyzk'
        
        try:
            # Dynamic import of zk
            from zk import ZK
            import zk.const as const
            
            # Connect to device
            zk = ZK(device_config['ip'], port=device_config['port'], 
                   timeout=60, password=device_config['password'])
            conn = zk.connect()
            
            if not conn:
                self.sync_status[device_name]['status'] = 'error'
                self.sync_status[device_name]['message'] = 'Failed to connect to device'
                return False, 'Failed to connect to device'
            
            self.sync_status[device_name]['status'] = 'reading'
            self.sync_status[device_name]['message'] = 'Reading attendance data...'
            
            # Get attendance data
            attendances = conn.get_attendance()
            
            if not attendances:
                self.sync_status[device_name]['status'] = 'completed'
                self.sync_status[device_name]['message'] = 'No new data found'
                conn.disconnect()
                return True, 'No new data found'
            
            # Filter by date range if provided
            filtered_data = []
            for att in attendances:
                if start_date and end_date:
                    if start_date <= att.timestamp.date() <= end_date:
                        filtered_data.append(att)
                else:
                    filtered_data.append(att)
            
            # Convert to FPLog format
            fplog_data = []
            
            # Get employee ATTID mapping
            print("Fetching employee ATTID mapping...")
            attid_mapping = self._get_employee_attid_mapping()
            fpid_mapped_count = 0
            
            for i, att in enumerate(filtered_data):
                print(f"Processing attendance record {i+1}: {att}")
                
                # Get PIN from attendance record
                pin = str(att.user_id).strip()
                
                # Get FPID from employee mapping (attid) based on PIN
                fpid_value = attid_mapping.get(pin)
                if fpid_value is not None:
                    fpid_mapped_count += 1
                    print(f"PIN {pin} mapped to ATTID {fpid_value}")
                else:
                    print(f"PIN {pin} not found in employees or attid is NULL")
                
                # Determine status using device-specific rules
                device_status = determine_status(device_name, att.punch)
                status_display = get_status_display(device_name, att.punch)
                
                print(f"Record {i+1}: PIN {pin}, Punch {att.punch} -> Status: {device_status} ({status_display})")
                
                # For device 201 (Fingerspot API), we need to preserve the original punch code
                # Store original punch code in fpid for device 201, ATTID mapping in different way
                if device_name == '201':
                    print(f"   -> Device 201: Storing original punch code {att.punch} in fpid field")
                    fplog_record = {
                        'PIN': pin,
                        'Date': att.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                        'Machine': device_name,
                        'Status': device_status,
                        'fpid': att.punch,  # Store original punch code for device 201
                        'attid': fpid_value  # Store ATTID separately (could be used in comments or other field)
                    }
                else:
                    fplog_record = {
                        'PIN': pin,
                        'Date': att.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                        'Machine': device_name,
                        'Status': device_status,
                        'fpid': fpid_value  # For other devices, use ATTID mapping
                    }
                
                fplog_data.append(fplog_record)
            
            print(f"FPID mapped for {fpid_mapped_count} out of {len(fplog_data)} records")
            
            conn.disconnect()
            
            return self._process_zk_fplog_data(device_name, fplog_data, fpid_mapped_count, start_date, end_date)
                
        except Exception as e:
            error_msg = f"Error syncing ZK device {device_name}: {str(e)}"
            self.sync_status[device_name]['status'] = 'error'
            self.sync_status[device_name]['message'] = error_msg
            return False, error_msg
        
        finally:
            self.sync_status[device_name]['end_time'] = datetime.now()
    
    def _sync_fingerspot_device(self, device_config, start_date=None, end_date=None):
        """Synchronize FPLog data from a Fingerspot API device"""
        device_name = device_config['name']
        
        if not self.fingerspot_service:
            error_msg = "Fingerspot service not available"
            self.sync_status[device_name]['status'] = 'error'
            self.sync_status[device_name]['message'] = error_msg
            self.sync_status[device_name]['end_time'] = datetime.now()
            return False, error_msg
        
        try:
            # Test connection first
            self.sync_status[device_name]['status'] = 'connecting'
            self.sync_status[device_name]['message'] = 'Testing Fingerspot API connection...'
            
            conn_success, conn_message = self.fingerspot_service.test_connection(device_config)
            if not conn_success:
                self.sync_status[device_name]['status'] = 'error'
                self.sync_status[device_name]['message'] = conn_message
                return False, conn_message
            
            # Sync data
            self.sync_status[device_name]['status'] = 'reading'
            self.sync_status[device_name]['message'] = 'Reading attendance data from Fingerspot API...'
            
            success, message, fplog_data = self.fingerspot_service.sync_device_data(
                device_config, start_date, end_date
            )
            
            if not success:
                self.sync_status[device_name]['status'] = 'error'
                self.sync_status[device_name]['message'] = message
                return False, message
            
            if not fplog_data:
                self.sync_status[device_name]['status'] = 'completed'
                self.sync_status[device_name]['message'] = 'No new data found'
                return True, 'No new data found'
            
            # Get employee ATTID mapping for Fingerspot devices too
            print("Fetching employee ATTID mapping for Fingerspot device...")
            attid_mapping = self._get_employee_attid_mapping()
            fpid_mapped_count = 0
            
            # Update fplog_data with ATTID mapping
            for record in fplog_data:
                pin = record['PIN']
                fpid_value = attid_mapping.get(pin)
                if fpid_value is not None:
                    record['fpid'] = fpid_value
                    fpid_mapped_count += 1
                    print(f"PIN {pin} mapped to ATTID {fpid_value}")
                else:
                    print(f"PIN {pin} not found in employees or attid is NULL")
            
            print(f"FPID mapped for {fpid_mapped_count} out of {len(fplog_data)} records")
            
            return self._process_fingerspot_fplog_data(device_name, fplog_data, fpid_mapped_count, start_date, end_date)
            
        except Exception as e:
            error_msg = f"Error syncing Fingerspot device {device_name}: {str(e)}"
            self.sync_status[device_name]['status'] = 'error'
            self.sync_status[device_name]['message'] = error_msg
            return False, error_msg
        
        finally:
            self.sync_status[device_name]['end_time'] = datetime.now()
    
    def _sync_online_attendance_device(self, device_config, start_date=None, end_date=None):
        """Synchronize attendance data from the online attendance API"""
        device_name = device_config['name']
        
        if not self.online_attendance_service:
            error_msg = "Online Attendance service not available"
            self.sync_status[device_name]['status'] = 'error'
            self.sync_status[device_name]['message'] = error_msg
            self.sync_status[device_name]['end_time'] = datetime.now()
            return False, error_msg

        try:
            # Update status to reading if not already set
            if self.sync_status[device_name]['status'] != 'reading':
                self.sync_status[device_name]['status'] = 'reading'
                self.sync_status[device_name]['message'] = 'Reading attendance data from Online Attendance API...'

            # Set default date range if not provided (e.g., today)
            if not start_date or not end_date:
                today = datetime.now().date()
                start_date = start_date or today
                end_date = end_date or today

            # Fetch data using the correct method
            start_date_str = start_date.strftime('%Y-%m-%d') if start_date else None
            end_date_str = end_date.strftime('%Y-%m-%d') if end_date else None
            
            success, message = self.online_attendance_service.sync_attendance_data(start_date_str, end_date_str)
            
            if not success:
                self.sync_status[device_name]['status'] = 'error'
                self.sync_status[device_name]['message'] = f'Failed to sync data from Online Attendance API: {message}'
                return False, message

            # Update status to completed after successful sync
            self.sync_status[device_name]['status'] = 'completed'
            self.sync_status[device_name]['end_time'] = datetime.now()
            
            # Extract record count from the message if available
            import re
            record_match = re.search(r'(\d+)\s+records?', message, re.IGNORECASE)
            if record_match:
                records_synced = int(record_match.group(1))
                self.sync_status[device_name]['records_synced'] = records_synced
                self.sync_status[device_name]['message'] = f"Online Attendance sync completed successfully: {message}"
                print(f"DEBUG: Online attendance sync completed with {records_synced} records")
            else:
                # If no record count found, try to get it from the service
                try:
                    # Get count of records processed today
                    from config.database import db_manager
                    conn = db_manager.get_connection()
                    cursor = conn.cursor()
                    
                    # Count today's online attendance records
                    today_str = datetime.now().strftime('%Y-%m-%d')
                    cursor.execute("""
                        SELECT COUNT(*) FROM gagalabsens 
                        WHERE machine = 'online:0' 
                        AND CONVERT(date, tgl) = ?
                    """, (today_str,))
                    
                    count_result = cursor.fetchone()
                    records_synced = count_result[0] if count_result else 0
                    
                    self.sync_status[device_name]['records_synced'] = records_synced
                    self.sync_status[device_name]['message'] = f"Online Attendance sync completed successfully. {records_synced} records found for {start_date_str} to {end_date_str}"
                    
                    conn.close()
                    print(f"DEBUG: Online attendance sync completed. Records found: {records_synced}")
                    
                except Exception as count_e:
                    print(f"Warning: Could not get record count: {count_e}")
                    self.sync_status[device_name]['records_synced'] = 0
                    self.sync_status[device_name]['message'] = f"Online Attendance sync completed successfully: {message}"
                    print("DEBUG: Online attendance sync completed without record count")
            
            print(f"DEBUG: Final status for {device_name}: {self.sync_status[device_name]}")
            return True, self.sync_status[device_name]['message']

        except Exception as e:
            error_msg = f"Error syncing Online Attendance device {device_name}: {str(e)}"
            self.sync_status[device_name]['status'] = 'error'
            self.sync_status[device_name]['message'] = error_msg
            self.sync_status[device_name]['end_time'] = datetime.now()
            print(f"DEBUG: Error in online attendance sync: {error_msg}")
            return False, error_msg
        finally:
            # Ensure end_time is always set
            if 'end_time' not in self.sync_status[device_name]:
                self.sync_status[device_name]['end_time'] = datetime.now()
            print(f"DEBUG: Finally block executed for {device_name}. Final status: {self.sync_status[device_name]['status']}")
    
    def _process_zk_fplog_data(self, device_name, fplog_data, fpid_mapped_count, start_date=None, end_date=None):
        """Process fplog data for ZK devices with specific handling"""
        if not fplog_data:
            self.sync_status[device_name]['status'] = 'completed'
            self.sync_status[device_name]['message'] = 'No data in date range'
            return True, 'No data in specified date range'
        
        # === ZK Device Processing ===
        self.sync_status[device_name]['status'] = 'processing'
        self.sync_status[device_name]['message'] = f'Processing {len(fplog_data)} ZK device records...'
        
        # Add to Attendance Queue with ZK-specific processing
        # self.sync_status[device_name]['status'] = 'queuing'
        # self.sync_status[device_name]['message'] = f'Adding {len(fplog_data)} ZK records to attendance queue with duplicate check...'
        
        # Prepare queue records for ZK devices
        # queue_records = []
        # for fplog_record in fplog_data:
        #     queue_record = {
        #         'pin': fplog_record['PIN'],
        #         'date': fplog_record['Date'],
        #         'status': 'baru',  # Default status for ZK devices
        #         'machine': fplog_record['Machine'],
        #         'punch_code': fplog_record.get('Status', None),
        #         'source_type': 'zk'  # Mark as ZK source
        #     }
        #     queue_records.append(queue_record)
        
        # # Add to attendance queue with enhanced duplicate check
        # queue_success, queue_message = self.attendance_model.bulk_add_to_attendance_queue_if_not_duplicate(queue_records)
        # if not queue_success:
        #     print(f"Warning: Failed to add ZK records to attendance queue: {queue_message}")
        # else:
        #     print(f"Successfully added ZK records to attendance queue with duplicate check: {queue_message}")
        
        # Sync to SQL Server FPLog with ZK-specific processing and duplicate check
        self.sync_status[device_name]['status'] = 'syncing'
        self.sync_status[device_name]['message'] = f'Syncing {len(fplog_data)} ZK records to FPLog table with duplicate check...'
        
        # Pass date range and device type to sync method with duplicate check
        success, message = self.attendance_model.sync_fplog_to_sqlserver_with_duplicate_check(
            fplog_data, 
            start_date.strftime('%Y-%m-%d') if start_date else None,
            end_date.strftime('%Y-%m-%d') if end_date else None
        )
        
        if success:
            self.sync_status[device_name]['status'] = 'completed'
            enhanced_message = f"{message} - ZK Device - FPID mapped for {fpid_mapped_count} records"
            self.sync_status[device_name]['message'] = enhanced_message
            self.sync_status[device_name]['records_synced'] = len(fplog_data)
            return True, enhanced_message
        else:
            self.sync_status[device_name]['status'] = 'error'
            error_message = f"ZK Device sync failed: {message}"
            self.sync_status[device_name]['message'] = error_message
            return False, error_message
    
    def _process_fingerspot_fplog_data(self, device_name, fplog_data, fpid_mapped_count, start_date=None, end_date=None):
        """Process fplog data for Fingerspot API devices with specific handling"""
        if not fplog_data:
            self.sync_status[device_name]['status'] = 'completed'
            self.sync_status[device_name]['message'] = 'No data in date range'
            return True, 'No data in specified date range'
        
        # === Fingerspot API Device Processing ===
        self.sync_status[device_name]['status'] = 'processing'
        self.sync_status[device_name]['message'] = f'Processing {len(fplog_data)} Fingerspot API records...'
        
        # Add to Attendance Queue with API-specific processing
        # self.sync_status[device_name]['status'] = 'queuing'
        # self.sync_status[device_name]['message'] = f'Adding {len(fplog_data)} Fingerspot API records to attendance queue with duplicate check...'
        
        # Prepare queue records for Fingerspot API devices
        queue_records = []
        for fplog_record in fplog_data:
            # For device 201, extract original punch code from fpid field
            punch_code = None
            if fplog_record['Machine'] == '201':
                # Device 201 uses punch as punch_code for attendance_queue
                punch_code = fplog_record.get('Punch', None)
            else:
                # For other devices, use fpid or fallback to Status
                punch_code = fplog_record.get('fpid', fplog_record.get('Status', None))
                
            queue_record = {
                'pin': fplog_record['PIN'],
                'date': fplog_record['Date'],
                'status': 'baru',  # Different status for API devices
                'machine': fplog_record['Machine'],
                'punch_code': punch_code,
                'source_type': 'fingerspot_api'  # Mark as API source
            }
            queue_records.append(queue_record)
        
        # Add to attendance queue with enhanced duplicate check
        # queue_success, queue_message = self.attendance_model.bulk_add_to_attendance_queue_if_not_duplicate(queue_records)
        # if not queue_success:
        #     print(f"Warning: Failed to add Fingerspot API records to attendance queue: {queue_message}")
        # else:
        #     print(f"Successfully added Fingerspot API records to attendance queue with duplicate check: {queue_message}")
        
        # Sync to SQL Server FPLog with API-specific processing and duplicate check
        self.sync_status[device_name]['status'] = 'syncing'
        self.sync_status[device_name]['message'] = f'Syncing {len(fplog_data)} Fingerspot API records to FPLog table with duplicate check...'
        
        # Pass date range and device type to sync method with duplicate check
        success, message = self.attendance_model.sync_fplog_to_sqlserver_with_duplicate_check(
            fplog_data, 
            start_date.strftime('%Y-%m-%d') if start_date else None,
            end_date.strftime('%Y-%m-%d') if end_date else None
        )
        
        if success:
            self.sync_status[device_name]['status'] = 'completed'
            enhanced_message = f"{message} - Fingerspot API Device - FPID mapped for {fpid_mapped_count} records"
            self.sync_status[device_name]['message'] = enhanced_message
            self.sync_status[device_name]['records_synced'] = len(fplog_data)
            return True, enhanced_message
        else:
            self.sync_status[device_name]['status'] = 'error'
            error_message = f"Fingerspot API Device sync failed: {message}"
            self.sync_status[device_name]['message'] = error_message
            return False, error_message
    

    
    def sync_all_devices(self, start_date=None, end_date=None, execute_procedures=True):
        """Synchronize FPLog data from all configured devices and optionally execute procedures"""
        results = {}
        
        # Start sync for each device in separate threads
        for device in self.devices:
            device_name = device['name']
            thread = threading.Thread(
                target=self._sync_device_thread,
                args=(device, start_date, end_date, results)
            )
            thread.daemon = True
            thread.start()
            self.sync_threads[device_name] = thread
        
        # Wait for all threads to complete if execute_procedures is True
        if execute_procedures:
            # Start a separate thread to wait for all devices and then execute procedures
            procedure_thread = threading.Thread(
                target=self._execute_procedures_after_sync,
                args=(start_date, end_date, results)
            )
            procedure_thread.daemon = True
            procedure_thread.start()
            
            return True, f"Started synchronization for {len(self.devices)} devices with automatic procedure execution"
        
        return True, f"Started synchronization for {len(self.devices)} devices"
    
    def _sync_device_thread(self, device, start_date, end_date, results):
        """Thread function for device synchronization"""
        device_name = device['name']
        success, message = self.sync_single_device(device, start_date, end_date)
        results[device_name] = {'success': success, 'message': message}
    
    def _execute_procedures_after_sync(self, start_date, end_date, results):
        """Execute stored procedures after all devices are synchronized"""
        # IMPROVED: Wait for all device sync to complete with proper status checking
        max_wait_time = 1800  # 30 minutes timeout (increased for slow device sync)
        wait_start = time.time()
        
        # Variable untuk menampung device yang telah selesai sync
        completed_devices_tracker = set()
        total_devices = len(self.devices)
        
        print(f"⏳ Waiting for all {total_devices} devices to complete synchronization before executing procedures...")
        print(f"⏰ Maximum wait time: {max_wait_time/60} minutes")
        
        while time.time() - wait_start < max_wait_time:
            # Reset tracker setiap iterasi untuk validasi ulang
            completed_devices_tracker.clear()
            
            # Cek status setiap device
            for device in self.devices:
                device_name = device['name']
                
                # Cek apakah device ada di sync_status dan statusnya completed atau error
                if device_name in self.sync_status:
                    device_status = self.sync_status[device_name].get('status', '')
                    
                    # Device dianggap selesai jika status: completed, error, atau cancelled
                    if device_status in ['completed', 'error', 'cancelled']:
                        completed_devices_tracker.add(device_name)
                        print(f"✓ Device '{device_name}' status: {device_status}")
            
            # Cek apakah semua device sudah selesai
            if len(completed_devices_tracker) == total_devices:
                print(f"✅ All {total_devices} devices have completed synchronization!")
                
                # CRITICAL: Add extra delay after all devices completed to ensure data is fully written
                extra_delay = 10  # 10 seconds safety delay
                print(f"⏸️  Adding {extra_delay} seconds safety delay to ensure all data is written to database...")
                time.sleep(extra_delay)
                print(f"✅ Safety delay completed. Ready to execute stored procedures.")
                
                break
            else:
                pending_count = total_devices - len(completed_devices_tracker)
                elapsed_time = int(time.time() - wait_start)
                print(f"⏳ Waiting... {len(completed_devices_tracker)}/{total_devices} devices completed. {pending_count} devices still syncing... (Elapsed: {elapsed_time}s)")
                time.sleep(5)  # Check every 5 seconds (reduced frequency)
        
        # Validasi akhir: Kategorisasi device berdasarkan status
        failed_devices = []
        running_devices = []
        successful_devices = []
        cancelled_devices = []
        
        for device in self.devices:
            device_name = device['name']
            
            if device_name in self.sync_status:
                device_status = self.sync_status[device_name].get('status', 'unknown')
                
                if device_status == 'completed':
                    successful_devices.append(device_name)
                elif device_status == 'error':
                    failed_devices.append(device_name)
                elif device_status == 'cancelled':
                    cancelled_devices.append(device_name)
                else:
                    # Status masih syncing, connecting, reading, dll (timeout)
                    running_devices.append(device_name)
            else:
                # Device tidak ada di sync_status (belum diproses)
                # Device tidak ada di sync_status (belum diproses)
                running_devices.append(device_name)
        
        # Log hasil final kategorisasi
        print(f"\n{'='*60}")
        print(f"DEVICE SYNCHRONIZATION SUMMARY")
        print(f"{'='*60}")
        print(f"✅ Successful: {len(successful_devices)} devices")
        if successful_devices:
            for dev in successful_devices:
                print(f"   - {dev}")
        
        print(f"❌ Failed: {len(failed_devices)} devices")
        if failed_devices:
            for dev in failed_devices:
                print(f"   - {dev}")
        
        print(f"⏸️  Cancelled: {len(cancelled_devices)} devices")
        if cancelled_devices:
            for dev in cancelled_devices:
                print(f"   - {dev}")
        
        print(f"⏳ Timeout/Still Running: {len(running_devices)} devices")
        if running_devices:
            for dev in running_devices:
                print(f"   - {dev}")
        print(f"{'='*60}\n")
        
        # Update sync status to show procedure execution phase
        procedure_status = {
            'status': 'waiting',
            'message': f'Device sync completed. Successful: {len(successful_devices)}, Failed: {len(failed_devices)}, Cancelled: {len(cancelled_devices)}, Timeout: {len(running_devices)}. Checking if procedures can be executed...',
            'start_time': datetime.now(),
            'successful_devices': successful_devices,
            'failed_devices': failed_devices,
            'cancelled_devices': cancelled_devices,
            'timeout_devices': running_devices,
            'total_devices': total_devices,
            'completed_devices_count': len(successful_devices) + len(failed_devices) + len(cancelled_devices)
        }
        
        # Add procedure status to sync_status
        self.sync_status['_procedures'] = procedure_status
        
        # CRITICAL CHECK: Hanya jalankan procedure jika SEMUA device sudah completed
        all_devices_finished = len(completed_devices_tracker) == total_devices
        
        if not all_devices_finished:
            error_msg = f"❌ PROCEDURE EXECUTION BLOCKED: Not all devices completed. {len(completed_devices_tracker)}/{total_devices} devices finished."
            print(error_msg)
            print(f"⚠️  Devices still syncing or timed out: {running_devices}")
            
            self.sync_status['_procedures']['status'] = 'blocked'
            self.sync_status['_procedures']['message'] = error_msg
            self.sync_status['_procedures']['end_time'] = datetime.now()
            print(f"Procedure execution BLOCKED: {error_msg}")
            return
        
        # Additional check: Pastikan minimal ada successful devices
        if len(successful_devices) == 0:
            error_msg = f"❌ PROCEDURE EXECUTION BLOCKED: No successful device synchronization."
            print(error_msg)
            
            self.sync_status['_procedures']['status'] = 'blocked'
            self.sync_status['_procedures']['message'] = error_msg
            self.sync_status['_procedures']['end_time'] = datetime.now()
            print(f"Procedure execution BLOCKED: {error_msg}")
            return
        
        # Jika ada device yang timeout, log warning tapi tetap lanjut jika mayoritas sukses
        if len(running_devices) > 0:
            warning_msg = f"⚠️  WARNING: {len(running_devices)} device(s) timed out but all devices reached final state. Proceeding with procedure execution..."
            print(warning_msg)
        
        print(f"✅ All {total_devices} devices have reached final state. Proceeding with stored procedure execution...")
        procedure_status['status'] = 'executing_procedures'
        procedure_status['message'] = f'All devices completed. Executing stored procedures...'
        
        # Execute stored procedures
        # If no date range provided, use default: 3 days ago to today
        if not start_date or not end_date:
            print("⚠️  No date range provided for sync. Using default: last 3 days")
            today = datetime.now().date()
            start_date = today - timedelta(days=3)
            end_date = today
            print(f"📅 Default date range set: {start_date} to {end_date} (3 days)")
        
        try:
            # Format dates for procedure execution
            start_date_str = start_date.strftime('%Y-%m-%d') if hasattr(start_date, 'strftime') else str(start_date)
            end_date_str = end_date.strftime('%Y-%m-%d') if hasattr(end_date, 'strftime') else str(end_date)
            
            print(f"Executing stored procedures for date range: {start_date_str} to {end_date_str}")
            
            # Execute attrecord procedure FIRST
            self.sync_status['_procedures']['message'] = 'Executing attrecord procedure...'
            print("🔄 Step 1: Executing attrecord procedure...")
            attrecord_success, attrecord_message = self.attendance_model.execute_attrecord_procedure(
                start_date_str, end_date_str
            )
            
            if attrecord_success:
                print(f"✅ Step 1 completed: attrecord procedure successful - {attrecord_message}")
                
                # Only execute spJamkerja if attrecord was successful
                self.sync_status['_procedures']['message'] = 'Executing spJamkerja procedure...'
                print("🔄 Step 2: Executing spJamkerja procedure...")
                spjamkerja_success, spjamkerja_message = self.attendance_model.execute_spjamkerja_procedure(
                    start_date_str, end_date_str
                )
                
                if spjamkerja_success:
                    print(f"✅ Step 2 completed: spJamkerja procedure successful - {spjamkerja_message}")
                else:
                    print(f"❌ Step 2 failed: spJamkerja procedure failed - {spjamkerja_message}")
            else:
                print(f"❌ Step 1 failed: attrecord procedure failed - {attrecord_message}")
                print("⚠️  Step 2 skipped: spJamkerja procedure will not be executed due to attrecord failure")
                spjamkerja_success = False
                spjamkerja_message = "Skipped due to attrecord procedure failure"
            
            # Update final status
            if attrecord_success and spjamkerja_success:
                self.sync_status['_procedures']['status'] = 'completed'
                self.sync_status['_procedures']['message'] = f'All procedures completed successfully. Device sync - Successful: {len(successful_devices)}, Failed: {len(failed_devices)}'
            else:
                self.sync_status['_procedures']['status'] = 'partial_error'
                error_details = []
                if not attrecord_success:
                    error_details.append(f"attrecord: {attrecord_message}")
                if not spjamkerja_success:
                    error_details.append(f"spJamkerja: {spjamkerja_message}")
                self.sync_status['_procedures']['message'] = f'Some procedures failed: {"; ".join(error_details)}'
            
            self.sync_status['_procedures']['attrecord_success'] = attrecord_success
            self.sync_status['_procedures']['attrecord_message'] = attrecord_message
            self.sync_status['_procedures']['spjamkerja_success'] = spjamkerja_success
            self.sync_status['_procedures']['spjamkerja_message'] = spjamkerja_message
                
        except Exception as e:
            error_msg = f"Error executing stored procedures: {str(e)}"
            print(f"❌ {error_msg}")
            self.sync_status['_procedures']['status'] = 'error'
            self.sync_status['_procedures']['message'] = error_msg
        
        self.sync_status['_procedures']['end_time'] = datetime.now()
        print(f"Procedure execution completed: {self.sync_status['_procedures']['message']}")
    
    
    def get_sync_status(self):
        """Get current synchronization status for all devices"""
        return self.sync_status
    
    def get_device_list(self):
        """Get list of configured devices"""
        device_status = []
        for device in self.devices:
            status_info = self.sync_status.get(device['name'], {
                'status': 'idle',
                'message': 'Ready to sync',
                'records_synced': 0
            })
            
            device_info = {
                'name': device['name'],
                'ip': device['ip'],
                'port': device['port'],
                'description': device.get('description', ''),
                'location': device.get('location', ''),
                'status': status_info['status'],
                'message': status_info['message'],
                'records_synced': status_info.get('records_synced', 0),
                'last_sync': status_info.get('end_time', None)
            }
            device_status.append(device_info)
        
        return device_status
    
    def get_device_sync_summary(self):
        """Get synchronization summary from database"""
        return self.attendance_model.get_device_sync_status()
    
    def _determine_status(self, punch_code, device_name):
        """Determine attendance status based on punch code and device (deprecated - use config.devices)"""
        return determine_status(device_name, punch_code)
    
    def cancel_sync(self, device_name=None):
        """Cancel ongoing synchronization"""
        if device_name:
            if device_name in self.sync_status:
                self.sync_status[device_name]['status'] = 'cancelled'
                self.sync_status[device_name]['message'] = 'Sync cancelled by user'
            return True, f"Sync cancelled for device {device_name}"
        else:
            # Cancel all
            for name in self.sync_status:
                if self.sync_status[name]['status'] in ['connecting', 'reading', 'syncing']:
                    self.sync_status[name]['status'] = 'cancelled'
                    self.sync_status[name]['message'] = 'Sync cancelled by user'
            return True, "All sync operations cancelled"
    
    def get_attendance_queue(self, status=None, limit=100):
        """Get attendance queue records"""
        return self.attendance_model.get_attendance_queue(status, limit)
    
    def update_queue_status(self, queue_id, new_status):
        """Update status of queue record"""
        return self.attendance_model.update_queue_status(queue_id, new_status)
    
    def delete_from_queue(self, queue_id):
        """Delete record from attendance queue"""
        return self.attendance_model.delete_from_queue(queue_id)
    
    def process_attendance_queue(self, batch_size=50):
        """Process attendance queue records with status 'baru'"""
        try:
            # Get records with status 'baru'
            queue_records = self.attendance_model.get_attendance_queue(status='baru', limit=batch_size)
            
            if not queue_records:
                return True, "No records to process in queue"
            
            processed_count = 0
            error_count = 0
            
            for record in queue_records:
                try:
                    # Mark as processing
                    self.attendance_model.update_queue_status(record['id'], 'diproses')
                    
                    # Process the record (you can add custom processing logic here)
                    # For example: validate data, transform data, etc.
                    
                    # Mark as completed
                    self.attendance_model.update_queue_status(record['id'], 'selesai')
                    processed_count += 1
                    
                except Exception as e:
                    # Mark as error
                    self.attendance_model.update_queue_status(record['id'], 'error')
                    error_count += 1
                    print(f"Error processing queue record {record['id']}: {e}")
            
            return True, f"Processed {processed_count} records, {error_count} errors"
            
        except Exception as e:
            return False, f"Error processing attendance queue: {str(e)}"
