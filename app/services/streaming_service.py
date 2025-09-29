import threading
import time
from datetime import datetime
from collections import deque
from config.database import db_manager
from config.devices import (
    FINGERPRINT_DEVICES,
    determine_status,
    get_status_display,
    get_device_display_name,
    get_zk_devices,
    get_fingerspot_api_devices
)
from app.models.attendance import AttendanceModel
from config.logging_config import get_streaming_logger

# Setup logging
logger = get_streaming_logger()

class StreamingService:
    """Service for handling real-time data streaming from fingerprint devices"""
    
    def __init__(self):
        self.db_manager = db_manager
        self.devices = FINGERPRINT_DEVICES
        self.running = False
        self.threads = []
        # Notification system
        self.notifications = deque(maxlen=100)  # Keep last 100 notifications
        self.notification_callbacks = []  # For real-time callbacks
        # Initialize attendance model for queue operations
        self.attendance_model = AttendanceModel()
        
        # Initialize Fingerspot API service
        try:
            from app.services.fingerspot_service import FingerspotAPIService
            self.fingerspot_service = FingerspotAPIService()
            logger.info("Fingerspot API service initialized successfully for streaming")
        except ImportError as e:
            self.fingerspot_service = None
            logger.warning(f"Fingerspot service not available for streaming - Import error: {e}")
        except Exception as e:
            self.fingerspot_service = None
            logger.warning(f"Fingerspot service not available for streaming - Initialization error: {e}")
        
        # Initialize Online Attendance service
        try:
            from app.services.online_attendance_service import OnlineAttendanceService
            self.online_attendance_service = OnlineAttendanceService()
            logger.info("Online Attendance service initialized successfully for streaming")
        except ImportError as e:
            self.online_attendance_service = None
            logger.warning(f"Online Attendance service not available for streaming - Import error: {e}")
        except Exception as e:
            self.online_attendance_service = None
            logger.warning(f"Online Attendance service not available for streaming - Initialization error: {e}")
    
    def add_notification_callback(self, callback):
        """Add a callback function for real-time notifications"""
        self.notification_callbacks.append(callback)
    
    def remove_notification_callback(self, callback):
        """Remove a notification callback"""
        if callback in self.notification_callbacks:
            self.notification_callbacks.remove(callback)
    
    def _add_notification(self, notification_type, device_name, user_id, status, timestamp):
        """Add a new notification to the queue"""
        notification = {
            'id': f"{device_name}_{user_id}_{int(timestamp.timestamp())}",
            'type': notification_type,
            'device_name': get_device_display_name(device_name),
            'user_id': user_id,
            'status': status,
            'status_display': get_status_display(device_name, determine_status(device_name, status)),
            'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'datetime': timestamp,
            'message': f"Absensi diterima PIN {user_id} mesin {get_device_display_name(device_name)}",
            'toast_message': f"Absensi diterima PIN {user_id} mesin {get_device_display_name(device_name)}"
        }
        
        self.notifications.append(notification)
        
        # Call notification callbacks
        for callback in self.notification_callbacks:
            try:
                callback(notification)
            except Exception as e:
                logger.error(f"Error calling notification callback: {e}")
    
    def _get_status_display(self, device_name, status):
        """Get human-readable status display (deprecated - use config.devices)"""
        return get_status_display(device_name, status)
    
    def get_recent_notifications(self, limit=20):
        """Get recent notifications"""
        notifications_list = list(self.notifications)
        notifications_list.sort(key=lambda x: x['datetime'], reverse=True)
        return notifications_list[:limit]
    
    def clear_notifications(self):
        """Clear all notifications"""
        self.notifications.clear()
        return True, "Notifications cleared"
    
    def start_streaming(self):
        """Start streaming from all devices"""
        if self.running:
            return False, "Streaming is already running"
        
        self.running = True
        self.threads = []
        
        for device in self.devices:
            thread = threading.Thread(
                target=self._handle_device, 
                args=(device,), 
                daemon=True
            )
            self.threads.append(thread)
            thread.start()
        
        return True, f"Started streaming from {len(self.devices)} devices"
    
    def stop_streaming(self):
        """Stop streaming from all devices with proper cleanup"""
        logger.info("Stopping streaming service...")
        self.running = False
        
        # Give threads time to gracefully shutdown
        if self.threads:
            logger.info(f"Waiting for {len(self.threads)} threads to finish...")
            
            # Wait for threads to finish (max 30 seconds)
            import time
            start_time = time.time()
            timeout = 30
            
            while any(t.is_alive() for t in self.threads) and (time.time() - start_time) < timeout:
                time.sleep(1)
            
            # Check if any threads are still alive
            alive_threads = [t for t in self.threads if t.is_alive()]
            if alive_threads:
                logger.warning(f"{len(alive_threads)} threads did not finish gracefully")
            else:
                logger.info("All threads finished gracefully")
            
            # Clear thread list
            self.threads.clear()
        
        logger.info("Streaming service stopped")
        return True, "Streaming stopped"
    
    def cleanup_resources(self):
        """Cleanup resources and connections"""
        try:
            # Stop streaming if running
            if self.running:
                self.stop_streaming()
            
            # Clear notifications
            self.notifications.clear()
            
            # Clear callbacks
            self.notification_callbacks.clear()
            
            logger.info("Resources cleaned up successfully")
            return True
        except Exception as e:
            logger.error(f"Error during resource cleanup: {e}")
            return False
    
    def get_streaming_status(self):
        """Get current streaming status"""
        return {
            'running': self.running,
            'devices_count': len(self.devices),
            'active_threads': len([t for t in self.threads if t.is_alive()]),
            'devices': [{'name': d['name'], 'ip': d['ip']} for d in self.devices],
            'recent_notifications': len(self.notifications),
            'last_notification': list(self.notifications)[-1] if self.notifications else None
        }
    
    def _handle_device(self, device_info):
        """Handle streaming from a single device (ZK or Fingerspot API)"""
        device_name = device_info['name']
        connection_type = device_info.get('connection_type', 'zk')
        
        logger.info(f"[{device_name}] Starting streaming thread for {connection_type} device...")
        
        # Route to appropriate streaming method based on connection type
        if connection_type == 'fingerspot_api':
            self._handle_fingerspot_device(device_info)
        elif connection_type == 'online_attendance':
            self._handle_online_attendance_device(device_info)
        else:
            self._handle_zk_device(device_info)
    
    def _handle_zk_device(self, device_info):
        """Handle streaming from a ZK device"""
        device_name = device_info['name']
        logger.info(f"[{device_name}] Starting ZK streaming thread...")
        
        try:
            from zk import ZK
        except ImportError:
            logger.error(f"[{device_name}] pyzk module not available. Cannot stream from ZK device.")
            return
        
        zk = ZK(device_info['ip'], port=device_info['port'], timeout=30, password=device_info['password'])
        
        while self.running:
            zk_conn = None
            db_conn = None
            cursor = None
            try:
                logger.info(f"[{device_name}] Connecting to ZK device...")
                zk_conn = zk.connect()
                logger.info(f"[{device_name}] ZK device connected successfully!")
                
                # Use connection pooling untuk database
                db_conn = self.db_manager.get_sqlserver_connection()
                if not db_conn:
                    raise Exception("Cannot get database connection")
                
                cursor = db_conn.cursor()
                logger.info(f"[{device_name}] Database connected successfully.")
                
                logger.info(f"[{device_name}] Waiting for attendance data...")
                
                # Set connection timeout untuk avoid hanging
                db_conn.timeout = 30
                
                for attendance in zk_conn.live_capture():
                    if not self.running:
                        break
                    
                    if attendance is None:
                        continue
                    
                    # Process ZK device attendance record
                    self._process_zk_attendance_record(device_name, attendance, cursor, db_conn)
                        
            except Exception as e:
                logger.error(f"[{device_name}] Streaming error: {e}. Retrying in 30 seconds...")
            finally:
                if zk_conn and zk_conn.is_connect:
                    zk_conn.disconnect()
                    logger.info(f"[{device_name}] Device connection closed.")
                if cursor:
                    try:
                        cursor.close()
                    except:
                        pass
                if db_conn:
                    try:
                        db_conn.close()
                        logger.info(f"[{device_name}] Database connection closed.")
                    except:
                        pass  # Connection might already be closed
            
            if self.running:
                time.sleep(30)  # Wait before retrying
    
    def _handle_fingerspot_device(self, device_info):
        """Handle streaming from a Fingerspot API device (polling-based)"""
        device_name = device_info['name']
        logger.info(f"[{device_name}] Starting Fingerspot API streaming thread...")
        
        if not self.fingerspot_service:
            logger.error(f"[{device_name}] Fingerspot service not available. Cannot stream from API device.")
            return
        
        # Test connection first using get_device endpoint
        logger.info(f"[{device_name}] Testing API connection...")
        connection_success, connection_message = self.fingerspot_service.test_connection(device_info)
        
        if not connection_success:
            logger.error(f"[{device_name}] API connection test failed: {connection_message}")
            return
        
        logger.info(f"[{device_name}] API connection successful: {connection_message}")
        
        # For API devices, we use polling instead of live streaming
        last_poll_time = datetime.now()
        poll_interval = 7200  # Poll every 7200 seconds (2 hours)

        while self.running:
            try:
                logger.info(f"[{device_name}] Polling Fingerspot API for new attendance data...")
                
                # Get attendance data from the last poll time
                end_time = datetime.now()
                
                # Get recent attendance data
                attendance_records = self.fingerspot_service.get_attendance_data(
                    device_info, 
                    start_date=last_poll_time,
                    end_date=end_time
                )
                
                if attendance_records:
                    logger.info(f"[{device_name}] Found {len(attendance_records)} new records from API")
                    
                    # Process each record
                    for attendance in attendance_records:
                        # Process Fingerspot API attendance record
                        self._process_fingerspot_attendance_record(device_name, attendance)
                else:
                    logger.debug(f"[{device_name}] No new records found in API poll")
                
                # Update last poll time
                last_poll_time = end_time
                
            except Exception as e:
                logger.error(f"[{device_name}] Fingerspot API streaming error: {e}. Retrying in {poll_interval} seconds...")
            
            # Wait for next poll
            if self.running:
                time.sleep(poll_interval)
    
    def _determine_status(self, device_name, punch):
        """Determine status based on device name and punch code (deprecated - use config.devices)"""
        return determine_status(device_name, punch)
    
    def _get_fpid_by_pin(self, pin):
        """Get fpid from employees table based on PIN. Returns None if not found."""
        try:
            conn = self.db_manager.get_sqlserver_connection()
            if not conn:
                logger.warning("Cannot get database connection for fpid lookup")
                return None
            
            cursor = conn.cursor()
            query = "SELECT attid FROM employees WHERE pin = ?"
            cursor.execute(query, (str(pin),))
            result = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            if result and result[0] is not None:
                logger.debug(f"   -> Found fpid {result[0]} for PIN {pin}")
                return int(result[0])
            else:
                logger.warning(f"   -> FPID not found for PIN {pin}, using NULL")
                return None
                
        except Exception as e:
            logger.error(f"   -> Error looking up fpid for PIN {pin}: {e}")
            return None
    
    def _process_zk_attendance_record(self, device_name, attendance, cursor, db_conn):
        """Process attendance record from ZK device"""
        logger.info(f"[{device_name}] ZK Data received: User ID: {attendance.user_id}, Time: {attendance.timestamp}")
        
        try:
            # Use config function to determine status with enhanced logging
            status_val = determine_status(device_name, attendance.punch)
            status_display = get_status_display(device_name, attendance.punch)
            
            if status_val is not None:
                # Validate and convert data types to prevent SQL Server errors
                pin = str(attendance.user_id) if attendance.user_id is not None else ''
                timestamp = attendance.timestamp
                machine = str(device_name) if device_name is not None else ''
                
                # Use status as-is since status column is varchar
                status = status_val
                logger.debug(f"   -> [{device_name}] ZK Punch code {attendance.punch} -> Status: {status} ({status_display})")
                
                # Get fpid from employee table based on PIN
                fpid = self._get_fpid_by_pin(pin)
                
                # Save to database with duplicate check
                success, message = self.attendance_model.add_fplog_record_if_not_duplicate(
                    pin=pin,
                    date=timestamp,
                    machine=machine,
                    status=status,
                    fpid=fpid
                )

                if success:
                    logger.info(f"   -> [{device_name}] ZK Data saved to FPLog: {message}")
                else:
                    logger.info(f"   -> [{device_name}] ZK Data not saved to FPLog: {message}")
                
                # Add to attendance queue for worker processing
                try:
                    # Convert timestamp to string format for queue
                    timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S') if isinstance(timestamp, datetime) else str(timestamp)
                    
                    queue_success, queue_message = self.attendance_model.add_to_attendance_queue_enhanced(
                        pin=pin,
                        date=timestamp_str,
                        status='baru',  # Queue status for ZK devices
                        machine=machine,
                        punch_code=attendance.punch  # Use the original punch code from machine
                    )
                    
                    if queue_success:
                        logger.info(f"   -> [{device_name}] ZK Data added to attendance queue: {queue_message}")
                    else:
                        logger.info(f"   -> [{device_name}] ZK Data not added to attendance queue: {queue_message}")
                        
                except Exception as queue_error:
                    logger.warning(f"   -> [{device_name}] Warning: Failed to add ZK data to attendance queue: {queue_error}")
                
                # Add notification for new data
                self._add_notification(
                    notification_type='attendance_received',
                    device_name=device_name,
                    user_id=attendance.user_id,
                    status=status_val,
                    timestamp=attendance.timestamp
                )
                
            else:
                logger.debug(f"   -> [{device_name}] ZK Status {attendance.punch} ignored.")
                
        except Exception as e:
            logger.error(f"   -> [{device_name}] Failed to save ZK data: {e}")
            # Add error notification
            self._add_notification(
                notification_type='error',
                device_name=device_name,
                message=f"Failed to save ZK attendance data: {e}",
                timestamp=attendance.timestamp
            )
    
    def _process_fingerspot_attendance_record(self, device_name, attendance):
        """Process attendance record from Fingerspot API device"""
        try:
            # Use config function to determine status
            status_val = determine_status(device_name, attendance.punch)
            status_display = get_status_display(device_name, attendance.punch)
            
            if status_val is not None:
                # Prepare data for database
                pin = str(attendance.user_id)
                timestamp = attendance.timestamp
                machine = str(device_name)
                status = status_val
                
                # Get fpid from employee table based on PIN
                fpid = self._get_fpid_by_pin(pin)
                
                logger.debug(f"   -> [{device_name}] Fingerspot API Punch code {attendance.punch} -> Status: {status} ({status_display})")
                
                # Save to database with duplicate check
                success, message = self.attendance_model.add_fplog_record_if_not_duplicate(
                    pin=pin,
                    date=timestamp,
                    machine=machine,
                    status=status,
                    fpid=fpid
                )

                if success:
                    logger.info(f"   -> [{device_name}] Fingerspot API Data saved to FPLog: {message}")
                else:
                    # Log the message, which will indicate if it was a duplicate or an error
                    logger.info(f"   -> [{device_name}] Fingerspot API Data not saved to FPLog: {message}")
                
                # Add to attendance queue
                try:
                    timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
                    
                    # For device 201, ensure punch_code is properly formatted
                    punch_code_for_queue = attendance.punch
                    if machine == '201':
                        # Device 201 menggunakan original status_scan sebagai punch_code
                        # Gunakan nilai original status_scan, bukan nilai yang sudah dikonversi
                        punch_code_for_queue = attendance.punch
                        logger.info(f"   -> [{device_name}] Using original status_scan '{punch_code_for_queue}' for punch_code")
                    else:
                        # Untuk device lain, pastikan punch_code adalah integer yang valid
                        try:
                            punch_code_for_queue = int(attendance.punch) if attendance.punch is not None else None
                        except (ValueError, TypeError):
                            logger.warning(f"   -> [{device_name}] Invalid punch code '{attendance.punch}', setting to None")
                            punch_code_for_queue = None
                    
                    queue_success, queue_message = self.attendance_model.add_to_attendance_queue_enhanced(
                        pin=pin,
                        date=timestamp_str,
                        status='baru',  # Different status for API devices
                        machine=machine,
                        punch_code=punch_code_for_queue
                    )
                    
                    if queue_success:
                        logger.info(f"   -> [{device_name}] Fingerspot API Data added to attendance queue: {queue_message}")
                    else:
                        logger.info(f"   -> [{device_name}] Fingerspot API Data not added to attendance queue: {queue_message}")
                        
                except Exception as queue_error:
                    logger.warning(f"   -> [{device_name}] Failed to add Fingerspot API data to attendance queue: {queue_error}")
                
                # Add notification
                self._add_notification(
                    notification_type='attendance_received',
                    device_name=device_name,
                    user_id=attendance.user_id,
                    status=status_val,
                    timestamp=attendance.timestamp
                )
                
            else:
                logger.debug(f"   -> [{device_name}] Fingerspot API Status {attendance.punch} ignored.")
                
        except Exception as e:
            logger.error(f"   -> [{device_name}] Failed to process Fingerspot API attendance record: {e}")
            # Add error notification
            self._add_notification(
                notification_type='error',
                device_name=device_name,
                message=f"Failed to process Fingerspot API attendance record: {e}",
                timestamp=attendance.timestamp if hasattr(attendance, 'timestamp') else datetime.now()
            )
    
    def _handle_online_attendance_device(self, device_info):
        """Handle streaming from Online Attendance API device with 3-hour schedule"""
        device_name = device_info['name']
        
        if not self.online_attendance_service:
            logger.error(f"[{device_name}] Online Attendance service not available for streaming")
            return
            
        logger.info(f"[{device_name}] Starting Online Attendance streaming with 3-hour schedule...")
        
        last_sync_time = datetime.now()
        sync_interval = 3 * 60 * 60  # 3 hours in seconds
        
        while self.running:
            try:
                current_time = datetime.now()
                time_since_last_sync = (current_time - last_sync_time).total_seconds()
                
                # Check if it's time for sync (every 3 hours)
                if time_since_last_sync >= sync_interval:
                    logger.info(f"[{device_name}] Starting scheduled sync (3-hour interval)...")
                    
                    # Perform sync
                    success, message = self.online_attendance_service.sync_attendance_data()
                    
                    if success:
                        logger.info(f"[{device_name}] Scheduled sync completed: {message}")
                        # Extract number of records from message if possible
                        import re
                        match = re.search(r'Saved: (\d+)', message)
                        records_synced = int(match.group(1)) if match else 0
                        
                        # Add success notification
                        self._add_notification(
                            notification_type='sync_completed',
                            device_name=device_name,
                            message=f"Scheduled sync completed. {message}",
                            timestamp=current_time,
                            records_count=records_synced
                        )
                    else:
                        logger.error(f"[{device_name}] Scheduled sync failed: {message}")
                        # Add error notification
                        self._add_notification(
                            notification_type='sync_error',
                            device_name=device_name,
                            message=f"Scheduled sync failed: {message}",
                            timestamp=current_time
                        )
                    
                    # Update last sync time
                    last_sync_time = current_time
                
                # Sleep for 5 minutes before checking again
                time.sleep(300)  # 5 minutes
                
            except Exception as e:
                logger.error(f"[{device_name}] Error in Online Attendance streaming: {e}")
                # Add error notification
                self._add_notification(
                    notification_type='error',
                    device_name=device_name,
                    message=f"Streaming error: {e}",
                    timestamp=datetime.now()
                )
                # Sleep before retrying
                time.sleep(60)  # 1 minute before retry
        
        logger.info(f"[{device_name}] Online Attendance streaming stopped")
