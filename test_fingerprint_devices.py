#!/usr/bin/env python3
"""
Test Tool untuk Fingerprint Devices
Tool untuk testing koneksi dan capture data dari mesin fingerprint
Mendukung semua tipe device: ZK, Fingerspot API, dan Online Attendance
"""

import sys
import os
import time
import threading
from datetime import datetime
import json

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.devices import (
    FINGERPRINT_DEVICES, 
    get_device_by_name, 
    determine_status,
    get_status_display,
    get_device_display_name
)
from config.database import db_manager
from config.logging_config import get_streaming_logger

# Setup logging
logger = get_streaming_logger()

class FingerprintDeviceTester:
    """Tool untuk testing fingerprint devices"""
    
    def __init__(self):
        self.db_manager = db_manager
        self.running = False
        self.selected_device = None
        self.test_thread = None
        
        # Initialize services
        self._init_services()
    
    def _init_services(self):
        """Initialize required services"""
        try:
            from app.services.fingerspot_service import FingerspotAPIService
            self.fingerspot_service = FingerspotAPIService()
            print("✅ Fingerspot API service initialized")
        except Exception as e:
            self.fingerspot_service = None
            print(f"⚠️  Fingerspot service not available: {e}")
        
        try:
            from app.services.online_attendance_service import OnlineAttendanceService
            self.online_attendance_service = OnlineAttendanceService()
            print("✅ Online Attendance service initialized")
        except Exception as e:
            self.online_attendance_service = None
            print(f"⚠️  Online Attendance service not available: {e}")
        
        # Initialize streaming service for manual attendance processing
        try:
            from app.services.streaming_service import StreamingService
            self.streaming_service = StreamingService()
            print("✅ Streaming service initialized")
        except Exception as e:
            self.streaming_service = None
            print(f"⚠️  Streaming service not available: {e}")
        
        # Initialize attendance model
        try:
            from app.models.attendance import AttendanceModel
            self.attendance_model = AttendanceModel()
            print("✅ Attendance model initialized")
        except Exception as e:
            self.attendance_model = None
            print(f"⚠️  Attendance model not available: {e}")
    
    def show_menu(self):
        """Display main menu"""
        print("\n" + "="*60)
        print("🔧 FINGERPRINT DEVICE TESTER")
        print("="*60)
        print("Available options:")
        print("1. List all devices")
        print("2. Select device for testing")
        print("3. Start attendance capture test")
        print("4. Stop test")
        print("5. Test device connection")
        print("6. Show test results")
        print("7. Manual PIN attendance (Full Process)")
        print("0. Exit")
        print("="*60)
    
    def list_devices(self):
        """List all available devices"""
        print("\n📱 Available Devices:")
        print("-" * 60)
        for i, device in enumerate(FINGERPRINT_DEVICES, 1):
            connection_type = device.get('connection_type', 'zk')
            status_icon = self._get_connection_icon(connection_type)
            
            print(f"{i:2d}. {device['name']:15} | {device['description']:20} | "
                  f"{connection_type:15} | {device['ip']:15} {status_icon}")
        print("-" * 60)
        print(f"Total devices: {len(FINGERPRINT_DEVICES)}")
    
    def _get_connection_icon(self, connection_type):
        """Get icon for connection type"""
        icons = {
            'zk': '⚡ ZK',
            'fingerspot_api': '🌐 API',
            'online_attendance': '☁️  Online'
        }
        return icons.get(connection_type, '❓ Unknown')
    
    def select_device(self):
        """Select device for testing"""
        self.list_devices()
        
        try:
            choice = input("\nEnter device number to select (0 to cancel): ").strip()
            
            if choice == '0':
                print("❌ Device selection cancelled")
                return
            
            device_index = int(choice) - 1
            
            if 0 <= device_index < len(FINGERPRINT_DEVICES):
                self.selected_device = FINGERPRINT_DEVICES[device_index]
                device_name = self.selected_device['name']
                connection_type = self.selected_device.get('connection_type', 'zk')
                
                print(f"\n✅ Selected device: {device_name} ({connection_type})")
                print(f"   Description: {self.selected_device.get('description', 'N/A')}")
                print(f"   IP: {self.selected_device['ip']}")
                print(f"   Port: {self.selected_device['port']}")
                
                return True
            else:
                print("❌ Invalid device number")
                return False
                
        except ValueError:
            print("❌ Invalid input. Please enter a number.")
            return False
    
    def test_connection(self):
        """Test connection to selected device"""
        if not self.selected_device:
            print("❌ No device selected. Please select a device first.")
            return
        
        device_name = self.selected_device['name']
        connection_type = self.selected_device.get('connection_type', 'zk')
        
        print(f"\n🔗 Testing connection to {device_name} ({connection_type})...")
        
        if connection_type == 'zk':
            success = self._test_zk_connection()
        elif connection_type == 'fingerspot_api':
            success = self._test_fingerspot_connection()
        elif connection_type == 'online_attendance':
            success = self._test_online_attendance_connection()
        else:
            print(f"❌ Unknown connection type: {connection_type}")
            return
        
        if success:
            print(f"✅ Connection to {device_name} successful!")
        else:
            print(f"❌ Connection to {device_name} failed!")
    
    def _test_zk_connection(self):
        """Test ZK device connection"""
        try:
            from zk import ZK
            
            device = self.selected_device
            zk = ZK(device['ip'], port=device['port'], timeout=10, password=device['password'])
            
            print(f"   Connecting to {device['ip']}:{device['port']}...")
            conn = zk.connect()
            
            if conn:
                print(f"   ✅ ZK device connected successfully")
                
                # Get device info
                firmware_version = conn.get_firmware_version()
                device_name = conn.get_device_name()
                
                print(f"   Device Name: {device_name}")
                print(f"   Firmware: {firmware_version}")
                
                conn.disconnect()
                return True
            else:
                print(f"   ❌ Failed to connect to ZK device")
                return False
                
        except ImportError:
            print("   ❌ pyzk module not available")
            return False
        except Exception as e:
            print(f"   ❌ ZK connection error: {e}")
            return False
    
    def _test_fingerspot_connection(self):
        """Test Fingerspot API connection"""
        if not self.fingerspot_service:
            print("   ❌ Fingerspot service not available")
            return False
        
        try:
            success, message = self.fingerspot_service.test_connection(self.selected_device)
            print(f"   {message}")
            return success
        except Exception as e:
            print(f"   ❌ Fingerspot API error: {e}")
            return False
    
    def _test_online_attendance_connection(self):
        """Test Online Attendance API connection"""
        if not self.online_attendance_service:
            print("   ❌ Online Attendance service not available")
            return False
        
        try:
            success, message = self.online_attendance_service.test_connection(self.selected_device)
            print(f"   {message}")
            return success
        except Exception as e:
            print(f"   ❌ Online Attendance API error: {e}")
            return False
    
    def start_test(self):
        """Start attendance capture test"""
        if not self.selected_device:
            print("❌ No device selected. Please select a device first.")
            return
        
        if self.running:
            print("⚠️  Test is already running. Stop current test first.")
            return
        
        device_name = self.selected_device['name']
        connection_type = self.selected_device.get('connection_type', 'zk')
        
        print(f"\n🚀 Starting attendance capture test for {device_name} ({connection_type})")
        print("📋 Press fingerprint on the device to capture attendance data")
        print("⏹️  Type 'stop' or press Ctrl+C to stop the test")
        
        self.running = True
        self.test_results = []
        
        # Start test thread based on device type
        if connection_type == 'zk':
            self.test_thread = threading.Thread(target=self._run_zk_test, daemon=True)
        elif connection_type == 'fingerspot_api':
            self.test_thread = threading.Thread(target=self._run_fingerspot_test, daemon=True)
        elif connection_type == 'online_attendance':
            self.test_thread = threading.Thread(target=self._run_online_test, daemon=True)
        else:
            print(f"❌ Unsupported connection type: {connection_type}")
            self.running = False
            return
        
        self.test_thread.start()
        
        # Wait for user input to stop
        self._wait_for_stop_command()
    
    def _wait_for_stop_command(self):
        """Wait for user to stop the test"""
        try:
            while self.running:
                user_input = input().strip().lower()
                if user_input in ['stop', 'exit', 'quit']:
                    self.stop_test()
                    break
        except KeyboardInterrupt:
            print("\n🛑 Test interrupted by user")
            self.stop_test()
    
    def _run_zk_test(self):
        """Run ZK device test"""
        try:
            from zk import ZK
            
            device = self.selected_device
            zk = ZK(device['ip'], port=device['port'], timeout=30, password=device['password'])
            
            print(f"🔌 Connecting to ZK device {device['name']}...")
            conn = zk.connect()
            
            if not conn:
                print("❌ Failed to connect to ZK device")
                return
            
            print("✅ Connected! Waiting for fingerprint scans...")
            
            for attendance in conn.live_capture():
                if not self.running:
                    break
                
                if attendance is None:
                    continue
                
                # Process attendance data
                self._process_attendance_data('zk', {
                    'user_id': attendance.user_id,
                    'timestamp': attendance.timestamp,
                    'punch': attendance.punch,
                    'device_name': device['name']
                })
            
            conn.disconnect()
            print("🔌 ZK device disconnected")
            
        except Exception as e:
            print(f"❌ ZK test error: {e}")
        finally:
            self.running = False
    
    def _run_fingerspot_test(self):
        """Run Fingerspot API test"""
        if not self.fingerspot_service:
            print("❌ Fingerspot service not available")
            return
        
        try:
            device_name = self.selected_device['name']
            print(f"🔌 Starting Fingerspot API polling for {device_name}...")
            
            last_poll = datetime.now()
            poll_interval = 30  # Poll every 30 seconds for testing
            
            while self.running:
                try:
                    current_time = datetime.now()
                    
                    # Get attendance data
                    attendance_records = self.fingerspot_service.get_attendance_data(
                        self.selected_device,
                        start_date=last_poll,
                        end_date=current_time
                    )
                    
                    if attendance_records:
                        print(f"📥 Found {len(attendance_records)} new records")
                        
                        for attendance in attendance_records:
                            self._process_attendance_data('fingerspot_api', {
                                'user_id': attendance.user_id,
                                'timestamp': attendance.timestamp,
                                'punch': attendance.punch,
                                'device_name': device_name
                            })
                    
                    last_poll = current_time
                    
                    # Sleep for poll interval
                    time.sleep(poll_interval)
                    
                except Exception as e:
                    print(f"⚠️  Fingerspot polling error: {e}")
                    time.sleep(poll_interval)
            
            print("🔌 Fingerspot API polling stopped")
            
        except Exception as e:
            print(f"❌ Fingerspot test error: {e}")
        finally:
            self.running = False
    
    def _run_online_test(self):
        """Run Online Attendance test"""
        if not self.online_attendance_service:
            print("❌ Online Attendance service not available")
            return
        
        try:
            device_name = self.selected_device['name']
            print(f"🔌 Starting Online Attendance sync for {device_name}...")
            
            poll_interval = 60  # Poll every 60 seconds for testing
            
            while self.running:
                try:
                    print("📡 Syncing with Online Attendance API...")
                    
                    success, message = self.online_attendance_service.sync_attendance_data()
                    
                    if success:
                        print(f"✅ Sync completed: {message}")
                        
                        # Extract number of records from message
                        import re
                        match = re.search(r'Fetched: (\d+)', message)
                        if match and int(match.group(1)) > 0:
                            records_count = int(match.group(1))
                            self._process_attendance_data('online_attendance', {
                                'records_count': records_count,
                                'message': message,
                                'timestamp': datetime.now(),
                                'device_name': device_name
                            })
                    else:
                        print(f"❌ Sync failed: {message}")
                    
                    # Sleep for poll interval
                    time.sleep(poll_interval)
                    
                except Exception as e:
                    print(f"⚠️  Online Attendance sync error: {e}")
                    time.sleep(poll_interval)
            
            print("🔌 Online Attendance sync stopped")
            
        except Exception as e:
            print(f"❌ Online Attendance test error: {e}")
        finally:
            self.running = False
    
    def _process_attendance_data(self, device_type, data):
        """Process captured attendance data"""
        timestamp = data.get('timestamp', datetime.now())
        device_name = data.get('device_name', 'Unknown')
        
        if device_type in ['zk', 'fingerspot_api']:
            user_id = data.get('user_id')
            punch = data.get('punch')
            
            # Determine status
            status = determine_status(device_name, punch)
            status_display = get_status_display(device_name, punch)
            
            result = {
                'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'device_name': device_name,
                'device_type': device_type,
                'user_id': user_id,
                'punch_code': punch,
                'status': status,
                'status_display': status_display
            }
            
            print(f"👆 FINGERPRINT DETECTED!")
            print(f"   Time: {result['timestamp']}")
            print(f"   Device: {device_name} ({device_type})")
            print(f"   User ID: {user_id}")
            print(f"   Punch Code: {punch}")
            print(f"   Status: {status} ({status_display})")
            print(f"   " + "-"*50)
            
        elif device_type == 'online_attendance':
            records_count = data.get('records_count', 0)
            message = data.get('message', '')
            
            result = {
                'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'device_name': device_name,
                'device_type': device_type,
                'records_count': records_count,
                'message': message
            }
            
            print(f"📡 ONLINE SYNC COMPLETED!")
            print(f"   Time: {result['timestamp']}")
            print(f"   Device: {device_name} ({device_type})")
            print(f"   Records: {records_count}")
            print(f"   Message: {message}")
            print(f"   " + "-"*50)
        
        # Store result
        if not hasattr(self, 'test_results'):
            self.test_results = []
        self.test_results.append(result)
    
    def stop_test(self):
        """Stop attendance capture test"""
        if not self.running:
            print("⚠️  No test is currently running")
            return
        
        print("\n🛑 Stopping test...")
        self.running = False
        
        if self.test_thread and self.test_thread.is_alive():
            self.test_thread.join(timeout=5)
        
        print("✅ Test stopped successfully")
    
    def show_results(self):
        """Show test results"""
        if not hasattr(self, 'test_results') or not self.test_results:
            print("\n📊 No test results available")
            return
        
        print(f"\n📊 Test Results ({len(self.test_results)} records)")
        print("="*80)
        
        for i, result in enumerate(self.test_results, 1):
            print(f"{i:3d}. {result['timestamp']} | {result['device_name']:15} | "
                  f"{result['device_type']:15} | ", end="")
            
            if 'user_id' in result:
                print(f"User: {result['user_id']:10} | "
                      f"Status: {result['status_display']}")
            else:
                print(f"Records: {result.get('records_count', 0)}")
        
        print("="*80)
        
        # Save to file
        try:
            filename = f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w') as f:
                json.dump(self.test_results, f, indent=2, default=str)
            print(f"💾 Results saved to: {filename}")
        except Exception as e:
            print(f"⚠️  Failed to save results: {e}")
    
    def manual_pin_attendance(self):
        """Manual PIN input for attendance with full processing"""
        if not self.selected_device:
            print("❌ No device selected. Please select a device first.")
            return
        
        if not self.attendance_model or not self.streaming_service:
            print("❌ Required services not available. Please check initialization.")
            return
        
        device_name = self.selected_device['name']
        connection_type = self.selected_device.get('connection_type', 'zk')
        
        print(f"\n🖐️  MANUAL PIN ATTENDANCE")
        print(f"Device: {device_name} ({connection_type})")
        print("="*60)
        
        try:
            # Get PIN input
            pin = input("Enter PIN/User ID: ").strip()
            if not pin:
                print("❌ PIN cannot be empty")
                return
            
            # Get punch code (optional for manual input)
            print("\nPunch codes:")
            print("0 = Check In (Masuk)")
            print("1 = Check Out (Keluar)")
            print("2 = Break Out")
            print("3 = Break In") 
            print("4 = Overtime In")
            print("5 = Overtime Out")
            punch_input = input("Enter punch code (0-5, default=0): ").strip()
            
            try:
                punch_code = int(punch_input) if punch_input else 0
                if punch_code < 0 or punch_code > 5:
                    punch_code = 0
            except ValueError:
                punch_code = 0
            
            # Option to skip FPID lookup if having database issues
            skip_fpid = input("\nSkip FPID lookup? (y/N): ").strip().lower() == 'y'
            
            # Create attendance timestamp
            attendance_time = datetime.now()
            
            print(f"\n🚀 Processing attendance...")
            print(f"   PIN: {pin}")
            print(f"   Punch Code: {punch_code}")
            print(f"   Device: {device_name}")
            print(f"   Time: {attendance_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"   FPID Lookup: {'Skipped' if skip_fpid else 'Enabled'}")
            print("-" * 50)
            
            # Process based on device type using streaming service logic
            if connection_type == 'zk':
                result = self._process_manual_zk_attendance(pin, punch_code, device_name, attendance_time, skip_fpid)
            elif connection_type == 'fingerspot_api':
                result = self._process_manual_fingerspot_attendance(pin, punch_code, device_name, attendance_time, skip_fpid)
            elif connection_type == 'online_attendance':
                result = self._process_manual_online_attendance(pin, punch_code, device_name, attendance_time, skip_fpid)
            else:
                print(f"❌ Unsupported device type: {connection_type}")
                return
            
            # Show results
            if result:
                print("\n✅ ATTENDANCE PROCESSED SUCCESSFULLY!")
                print("=" * 60)
                print(f"Final Status: {result['status_display']}")
                print(f"Database Status: {result['db_status']}")
                print(f"Queue Status: {result['queue_status']}")
                print(f"AttRecord Status: {result['attrecord_status']}")
                print("=" * 60)
                
                # Store in test results
                if not hasattr(self, 'test_results'):
                    self.test_results = []
                self.test_results.append({
                    'timestamp': attendance_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'device_name': device_name,
                    'device_type': f'manual_{connection_type}',
                    'user_id': pin,
                    'punch_code': punch_code,
                    'status': result['status'],
                    'status_display': result['status_display'],
                    'processing_result': result
                })
            else:
                print("\n❌ ATTENDANCE PROCESSING FAILED!")
                
        except KeyboardInterrupt:
            print("\n❌ Process cancelled by user")
        except Exception as e:
            print(f"\n❌ Error processing attendance: {e}")
    
    def _process_manual_zk_attendance(self, pin, punch_code, device_name, timestamp, skip_fpid=False):
        """Process manual ZK attendance using streaming service logic"""
        from config.devices import determine_status, get_status_display
        
        try:
            print("📝 Processing as ZK device attendance...")
            
            # Determine status like streaming service
            status_val = determine_status(device_name, punch_code)
            status_display = get_status_display(device_name, punch_code)
            
            if status_val is None:
                print(f"❌ Could not determine status for punch code {punch_code}")
                return None
            
            print(f"   Status determined: {status_val} ({status_display})")
            
            # Get fpid from employee table based on PIN (if not skipped)
            fpid = None
            if not skip_fpid:
                fpid = self._get_fpid_by_pin(pin)
                if fpid:
                    print(f"   FPID found: {fpid}")
                else:
                    print(f"   FPID not found for PIN {pin}, will use NULL")
            else:
                print(f"   FPID lookup skipped (using NULL)")
            
            # Save to FPLog database with duplicate check
            db_success, db_message = self.attendance_model.add_fplog_record_if_not_duplicate(
                pin=pin,
                date=timestamp,
                machine=device_name,
                status=status_val,
                fpid=fpid
            )
            
            print(f"   FPLog save: {'✅' if db_success else '❌'} {db_message}")
            
            # Execute attrecord procedure 
            attrecord_status = "Not executed"
            if db_success:
                try:
                    today_str = timestamp.strftime('%Y-%m-%d')
                    attrecord_success, attrecord_message = self.attendance_model.execute_attrecord_procedure_with_pins(
                        start_date=today_str,
                        end_date=today_str,
                        pins=[pin]
                    )
                    attrecord_status = f"{'✅' if attrecord_success else '❌'} {attrecord_message}"
                    print(f"   AttRecord: {attrecord_status}")
                except Exception as e:
                    attrecord_status = f"❌ Error: {e}"
                    print(f"   AttRecord: {attrecord_status}")
            
            # Add to attendance queue
            queue_status = "Not added"
            try:
                timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
                queue_success, queue_message = self.attendance_model.add_to_attendance_queue_enhanced(
                    pin=pin,
                    date=timestamp_str,
                    status='baru',
                    machine=device_name,
                    punch_code=punch_code
                )
                queue_status = f"{'✅' if queue_success else 'ℹ️'} {queue_message}"
                print(f"   Queue: {queue_status}")
            except Exception as e:
                queue_status = f"❌ Error: {e}"
                print(f"   Queue: {queue_status}")
            
            return {
                'status': status_val,
                'status_display': status_display,
                'db_status': db_message,
                'queue_status': queue_status,
                'attrecord_status': attrecord_status,
                'fpid': fpid
            }
            
        except Exception as e:
            print(f"❌ Error in ZK processing: {e}")
            return None
    
    def _process_manual_fingerspot_attendance(self, pin, punch_code, device_name, timestamp, skip_fpid=False):
        """Process manual Fingerspot attendance using streaming service logic"""
        from config.devices import determine_status, get_status_display
        
        try:
            print("📝 Processing as Fingerspot API attendance...")
            
            # Same logic as ZK but with fingerspot specific handling
            status_val = determine_status(device_name, punch_code)
            status_display = get_status_display(device_name, punch_code)
            
            if status_val is None:
                print(f"❌ Could not determine status for punch code {punch_code}")
                return None
            
            print(f"   Status determined: {status_val} ({status_display})")
            
            # Get fpid (if not skipped)
            fpid = None
            if not skip_fpid:
                fpid = self._get_fpid_by_pin(pin)
                if fpid:
                    print(f"   FPID found: {fpid}")
                else:
                    print(f"   FPID not found for PIN {pin}, will use NULL")
            else:
                print(f"   FPID lookup skipped (using NULL)")
            
            # Save to FPLog database
            db_success, db_message = self.attendance_model.add_fplog_record_if_not_duplicate(
                pin=pin,
                date=timestamp,
                machine=device_name,
                status=status_val,
                fpid=fpid
            )
            
            print(f"   FPLog save: {'✅' if db_success else '❌'} {db_message}")
            
            # Execute attrecord procedure
            attrecord_status = "Not executed"
            if db_success:
                try:
                    today_str = timestamp.strftime('%Y-%m-%d')
                    attrecord_success, attrecord_message = self.attendance_model.execute_attrecord_procedure_with_pins(
                        start_date=today_str,
                        end_date=today_str,
                        pins=[pin]
                    )
                    attrecord_status = f"{'✅' if attrecord_success else '❌'} {attrecord_message}"
                    print(f"   AttRecord: {attrecord_status}")
                except Exception as e:
                    attrecord_status = f"❌ Error: {e}"
                    print(f"   AttRecord: {attrecord_status}")
            
            # Add to attendance queue
            queue_status = "Not added"
            try:
                timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
                queue_success, queue_message = self.attendance_model.add_to_attendance_queue_enhanced(
                    pin=pin,
                    date=timestamp_str,
                    status='baru',
                    machine=device_name,
                    punch_code=punch_code
                )
                queue_status = f"{'✅' if queue_success else 'ℹ️'} {queue_message}"
                print(f"   Queue: {queue_status}")
            except Exception as e:
                queue_status = f"❌ Error: {e}"
                print(f"   Queue: {queue_status}")
            
            return {
                'status': status_val,
                'status_display': status_display,
                'db_status': db_message,
                'queue_status': queue_status,
                'attrecord_status': attrecord_status,
                'fpid': fpid
            }
            
        except Exception as e:
            print(f"❌ Error in Fingerspot processing: {e}")
            return None
    
    def _process_manual_online_attendance(self, pin, punch_code, device_name, timestamp, skip_fpid=False):
        """Process manual Online Attendance using hybrid approach (gagalabsens + attrecord)"""
        from config.devices import determine_status, get_status_display
        
        try:
            print("📝 Processing as Online Attendance (hybrid approach)...")
            
            # Determine status
            status_val = determine_status(device_name, punch_code)
            status_display = get_status_display(device_name, punch_code)
            
            if status_val is None:
                print(f"❌ Could not determine status for punch code {punch_code}")
                return None
            
            print(f"   Status determined: {status_val} ({status_display})")
            
            # For Online Attendance, save to gagalabsens instead of FPLog
            db_status = "Saved to gagalabsens"
            try:
                # Save to gagalabsens table
                gagal_success, gagal_message = self.attendance_model.add_gagalabsens_record(
                    pin=pin,
                    tanggal=timestamp.strftime('%Y-%m-%d'),
                    jam=timestamp.strftime('%H:%M:%S'),
                    status=status_val,
                    mesin=device_name
                )
                db_status = f"{'✅' if gagal_success else '❌'} Gagalabsens: {gagal_message}"
                print(f"   Gagalabsens save: {db_status}")
            except Exception as e:
                db_status = f"❌ Gagalabsens error: {e}"
                print(f"   Gagalabsens save: {db_status}")
            
            # Execute attrecord procedure (same as other devices)
            attrecord_status = "Not executed"
            try:
                today_str = timestamp.strftime('%Y-%m-%d')
                attrecord_success, attrecord_message = self.attendance_model.execute_attrecord_procedure_with_pins(
                    start_date=today_str,
                    end_date=today_str,
                    pins=[pin]
                )
                attrecord_status = f"{'✅' if attrecord_success else '❌'} {attrecord_message}"
                print(f"   AttRecord: {attrecord_status}")
            except Exception as e:
                attrecord_status = f"❌ Error: {e}"
                print(f"   AttRecord: {attrecord_status}")
            
            # No queue for online attendance - direct processing
            queue_status = "Not applicable (direct processing)"
            print(f"   Queue: {queue_status}")
            
            return {
                'status': status_val,
                'status_display': status_display,
                'db_status': db_status,
                'queue_status': queue_status,
                'attrecord_status': attrecord_status,
                'fpid': None  # Not used for online attendance
            }
            
        except Exception as e:
            print(f"❌ Error in Online Attendance processing: {e}")
            return None
    
    def _get_fpid_by_pin(self, pin):
        """Get FPID from employees table based on PIN"""
        try:
            conn = self.db_manager.get_sqlserver_connection()
            if not conn:
                return None
            
            cursor = conn.cursor()
            
            # Try the standard employees table first (like streaming service)
            try:
                cursor.execute("SELECT attid FROM employees WHERE pin = ?", (str(pin),))
                row = cursor.fetchone()
                
                if row and row[0] is not None:
                    cursor.close()
                    conn.close()
                    return int(row[0])
                    
            except Exception as e:
                # If employees table doesn't exist or has different structure, try alternatives
                print(f"   Warning: Could not query employees table: {e}")
                
                # Try alternative table names/structures
                alternative_queries = [
                    ("SELECT fpid FROM employee WHERE pin = ?", "employee table with fpid"),
                    ("SELECT id FROM pegawai WHERE pin = ?", "pegawai table"),
                    ("SELECT userid FROM userinfo WHERE badgenumber = ?", "userinfo table"),
                    ("SELECT emp_id FROM emp_master WHERE emp_code = ?", "emp_master table")
                ]
                
                for query, description in alternative_queries:
                    try:
                        cursor.execute(query, (str(pin),))
                        row = cursor.fetchone()
                        
                        if row and row[0] is not None:
                            print(f"   Found FPID using {description}")
                            cursor.close()
                            conn.close()
                            return int(row[0])
                            
                    except Exception:
                        continue  # Try next alternative
            
            cursor.close()
            conn.close()
            print(f"   No FPID found for PIN {pin} in any available table")
            return None
            
        except Exception as e:
            print(f"   Warning: Could not get FPID for PIN {pin}: {e}")
            return None
    
    def run(self):
        """Main application loop"""
        print("🚀 Starting Fingerprint Device Tester...")
        print("📱 Initializing services...")
        
        try:
            while True:
                self.show_menu()
                
                try:
                    choice = input("\nSelect option: ").strip()
                    
                    if choice == '0':
                        print("👋 Goodbye!")
                        break
                    elif choice == '1':
                        self.list_devices()
                    elif choice == '2':
                        self.select_device()
                    elif choice == '3':
                        self.start_test()
                    elif choice == '4':
                        self.stop_test()
                    elif choice == '5':
                        self.test_connection()
                    elif choice == '6':
                        self.show_results()
                    elif choice == '7':
                        self.manual_pin_attendance()
                    else:
                        print("❌ Invalid option. Please try again.")
                        
                except KeyboardInterrupt:
                    print("\n\n🛑 Interrupted by user")
                    break
                except Exception as e:
                    print(f"❌ Error: {e}")
                
                input("\nPress Enter to continue...")
                
        except Exception as e:
            print(f"💥 Fatal error: {e}")
        finally:
            if self.running:
                self.stop_test()
            print("🔚 Fingerprint Device Tester terminated")


def main():
    """Main entry point"""
    try:
        tester = FingerprintDeviceTester()
        tester.run()
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"💥 Fatal error: {e}")


if __name__ == "__main__":
    main()