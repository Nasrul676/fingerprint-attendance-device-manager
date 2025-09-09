"""
Mock sync service for testing without pyzk dependency
This service simulates device sync for testing the interface
"""
import threading
import time
from datetime import datetime, timedelta
from app.models.attendance import AttendanceModel
from config.config import Config
from config.devices import FINGERPRINT_DEVICES
import random

class MockSyncService:
    """Mock service for testing sync functionality without pyzk"""
    
    def __init__(self):
        self.attendance_model = AttendanceModel()
        # Use only first 2 devices for mock testing
        self.devices = FINGERPRINT_DEVICES[:2]
        self.sync_threads = {}
        self.sync_status = {}
        
    def _get_device_config(self):
        """Get device configuration from config (deprecated - now using FINGERPRINT_DEVICES)"""
        return FINGERPRINT_DEVICES[:2]  # Use first 2 devices for mock testing
    
    def sync_single_device(self, device_config, start_date=None, end_date=None):
        """Mock synchronization for testing"""
        device_name = device_config['name']
        self.sync_status[device_name] = {
            'status': 'connecting',
            'message': 'Connecting to device...',
            'start_time': datetime.now(),
            'records_synced': 0
        }
        
        try:
            # Simulate connection time
            time.sleep(2)
            
            self.sync_status[device_name]['status'] = 'reading'
            self.sync_status[device_name]['message'] = 'Reading attendance data...'
            
            # Simulate reading time
            time.sleep(3)
            
            # Generate mock FPLog data
            fplog_data = self._generate_mock_data(device_name, start_date, end_date)
            
            if not fplog_data:
                self.sync_status[device_name]['status'] = 'completed'
                self.sync_status[device_name]['message'] = 'No new data found'
                return True, 'No new data found'
            
            # Simulate sync to SQL Server
            self.sync_status[device_name]['status'] = 'syncing'
            self.sync_status[device_name]['message'] = f'Syncing {len(fplog_data)} records...'
            
            time.sleep(2)
            
            success, message = self.attendance_model.sync_fplog_to_sqlserver(fplog_data)
            
            if success:
                self.sync_status[device_name]['status'] = 'completed'
                self.sync_status[device_name]['message'] = f'Successfully synced {len(fplog_data)} records'
                self.sync_status[device_name]['records_synced'] = len(fplog_data)
                return True, f'Successfully synced {len(fplog_data)} records'
            else:
                self.sync_status[device_name]['status'] = 'error'
                self.sync_status[device_name]['message'] = message
                return False, message
                
        except Exception as e:
            error_msg = f"Error syncing device {device_name}: {str(e)}"
            self.sync_status[device_name]['status'] = 'error'
            self.sync_status[device_name]['message'] = error_msg
            return False, error_msg
        
        finally:
            self.sync_status[device_name]['end_time'] = datetime.now()
    
    def _generate_mock_data(self, device_name, start_date=None, end_date=None):
        """Generate mock FPLog data for testing"""
        mock_data = []
        
        # Generate random number of records (5-20)
        num_records = random.randint(5, 20)
        
        for i in range(num_records):
            # Random user ID
            user_id = random.randint(1, 100)
            
            # Random date within range or recent dates
            if start_date and end_date:
                start_dt = datetime.combine(start_date, datetime.min.time())
                end_dt = datetime.combine(end_date, datetime.max.time())
                random_date = start_dt + timedelta(
                    seconds=random.randint(0, int((end_dt - start_dt).total_seconds()))
                )
            else:
                # Random date in last 30 days
                days_ago = random.randint(0, 30)
                random_date = datetime.now() - timedelta(days=days_ago)
                random_date = random_date.replace(
                    hour=random.randint(6, 22),
                    minute=random.randint(0, 59),
                    second=random.randint(0, 59)
                )
            
            # Random punch code (0=in, 1=out)
            punch_code = random.randint(0, 1)
            
            mock_data.append({
                'PIN': str(user_id).zfill(3),
                'Date': random_date.strftime('%Y-%m-%d %H:%M:%S'),
                'Machine': device_name,
                'Status': punch_code + 1,  # 1=in, 2=out
                'fpid': punch_code
            })
        
        return mock_data
    
    def sync_all_devices(self, start_date=None, end_date=None):
        """Synchronize FPLog data from all configured devices"""
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
        
        return True, f"Started synchronization for {len(self.devices)} devices"
    
    def _sync_device_thread(self, device, start_date, end_date, results):
        """Thread function for device synchronization"""
        device_name = device['name']
        success, message = self.sync_single_device(device, start_date, end_date)
        results[device_name] = {'success': success, 'message': message}
    
    def get_sync_status(self):
        """Get current synchronization status for all devices"""
        return self.sync_status
    
    def get_device_list(self):
        """Get list of configured devices"""
        device_status = []
        for device in self.devices:
            status_info = self.sync_status.get(device['name'], {
                'status': 'idle',
                'message': 'Ready to sync (Mock Mode)',
                'records_synced': 0
            })
            
            device_info = {
                'name': device['name'],
                'ip': device['ip'],
                'port': device['port'],
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

    def test_device_connection(self, device_config):
        """Mock device connection test"""
        device_name = device_config['name']
        
        # Simulate connection test
        time.sleep(1)
        
        # Mock successful connection with fake device info
        device_info = {
            'firmware': 'Mock v1.0.0',
            'users_count': random.randint(50, 200),
            'attendance_count': random.randint(1000, 5000)
        }
        
        return True, 'Connection successful (Mock Mode)', device_info
