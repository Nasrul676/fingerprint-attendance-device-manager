"""
Fingerspot API Service for handling attendance data from Fingerspot devices
This service handles devices 201 and 203 that use Fingerspot Developer API
"""

import requests
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from config.devices import (
    get_fingerspot_api_devices,
    get_fingerspot_config,
    FINGERSPOT_API_CONFIG,
    determine_status,
    get_status_display
)
from config.logging_config import get_streaming_logger

# Setup logging
logger = get_streaming_logger()

class FingerspotAttendance:
    """Data class for Fingerspot attendance record"""
    def __init__(self, user_id: str, timestamp: datetime, punch: int, uid: int = None):
        self.user_id = user_id
        self.timestamp = timestamp
        self.punch = punch
        self.uid = uid

class FingerspotAPIService:
    """Service for handling Fingerspot API communication"""
    
    def __init__(self):
        self.base_config = FINGERSPOT_API_CONFIG
        self.timeout = self.base_config.get('timeout', 30)
        
    def _make_request(self, method: str, url: str, device_config: Dict, **kwargs) -> Optional[Dict]:
        """Make HTTP request to Fingerspot API with error handling and retries"""
        
        api_config = device_config.get('api_config', {})
        api_key = api_config.get('api_key', self.base_config.get('api_key'))
        
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        # Add headers to kwargs
        if 'headers' in kwargs:
            kwargs['headers'].update(headers)
        else:
            kwargs['headers'] = headers
        
        # Set timeout
        kwargs.setdefault('timeout', self.timeout)
        
        retry_count = api_config.get('retry_count', self.base_config.get('retry_count', 3))
        retry_delay = 2
        
        for attempt in range(retry_count):
            try:
                logger.debug(f"API Request (attempt {attempt + 1}): {method} {url}")
                
                if method.upper() == 'POST':
                    response = requests.post(url, **kwargs)
                elif method.upper() == 'GET':
                    response = requests.get(url, **kwargs)
                else:
                    logger.error(f"Unsupported HTTP method: {method}")
                    return None
                
                # Log response
                logger.debug(f"API Response: {response.status_code} - {response.text[:500]}")
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"API request failed with status {response.status_code}: {response.text}")
                    
            except requests.exceptions.ConnectTimeout:
                logger.error(f"Connection timeout to {url} (attempt {attempt + 1})")
            except requests.exceptions.ReadTimeout:
                logger.error(f"Read timeout from {url} (attempt {attempt + 1})")
            except requests.exceptions.ConnectionError as e:
                logger.error(f"Connection error to {url}: {e} (attempt {attempt + 1})")
            except requests.exceptions.RequestException as e:
                logger.error(f"Request error to {url}: {e} (attempt {attempt + 1})")
            except Exception as e:
                logger.error(f"Unexpected error during API request to {url}: {e}")
                return None
            
            # Retry logic
            if attempt < retry_count - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                import time
                time.sleep(retry_delay)
            else:
                logger.error(f"All retry attempts failed for {url}")
                return None
        
        return None

    def test_connection(self, device_config: Dict) -> Tuple[bool, str]:
        """
        Test connection to Fingerspot API using get_device endpoint
        
        Args:
            device_config: Device configuration
            
        Returns:
            Tuple of (success, message)
        """
        device_name = device_config.get('name')
        api_config = device_config.get('api_config', {})
        
        if not api_config:
            return False, f"No API config found for device {device_name}"
        
        # Build API URL for device endpoint
        base_url = api_config.get('base_url', self.base_config['base_url'])
        cloud_id = api_config.get('cloud_id')
        endpoint = self.base_config['endpoints']['devices']  # /get_device
        
        url = f"{base_url}{endpoint}"
        
        # Prepare request data (trans_id is required)
        data = {
            'trans_id': 1,
            'cloud_id': cloud_id
        }
        
        try:
            logger.info(f"Testing Fingerspot API connection for device {device_name}")
            response_data = self._make_request('POST', url, device_config, json=data)
            
            if not response_data:
                return False, f"No response from Fingerspot API for device {device_name}"
            
            # Check if request was successful
            if response_data.get('success'):
                device_info = response_data.get('data', {})
                device_api_name = device_info.get('device_name', 'Unknown')
                logger.info(f"Connection successful. Device: {device_api_name}")
                return True, f"Connection successful for device {device_name}"
            else:
                error_msg = response_data.get('message', 'Unknown error')
                logger.error(f"API returned error for device {device_name}: {error_msg}")
                return False, f"API error: {error_msg}"
                
        except Exception as e:
            error_msg = f"Connection test failed for device {device_name}: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def get_attendance_data(self, device_config: Dict, start_date: datetime = None, end_date: datetime = None) -> List[FingerspotAttendance]:
        """
        Get attendance data from Fingerspot API for a specific device
        
        Args:
            device_config: Device configuration with API settings
            start_date: Start date for data retrieval
            end_date: End date for data retrieval
        
        Returns:
            List of FingerspotAttendance objects
        """
        device_name = device_config.get('name')
        api_config = device_config.get('api_config', {})
        
        if not api_config:
            logger.error(f"No API config found for device {device_name}")
            return []
        
        # Build API URL
        base_url = api_config.get('base_url', self.base_config['base_url'])
        cloud_id = api_config.get('cloud_id')
        endpoint = self.base_config['endpoints']['attendance']
        
        url = f"{base_url}{endpoint}"
        
        # Prepare request data for POST (trans_id is required based on testing)
        data = {
            'trans_id': 1,
            'cloud_id': cloud_id
        }
        
        # Add date filters if provided (max 2 days range as per API limitation)
        if start_date and end_date:
            # Ensure date range is not more than 2 days
            date_diff = (end_date - start_date).days
            if date_diff > 2:
                logger.warning(f"Date range too large ({date_diff} days), limiting to 2 days")
                end_date = start_date + timedelta(days=2)
            
            data['start_date'] = start_date.strftime('%Y-%m-%d')
            data['end_date'] = end_date.strftime('%Y-%m-%d')
        elif start_date:
            data['start_date'] = start_date.strftime('%Y-%m-%d')
            data['end_date'] = start_date.strftime('%Y-%m-%d')
        elif end_date:
            data['start_date'] = end_date.strftime('%Y-%m-%d')
            data['end_date'] = end_date.strftime('%Y-%m-%d')
        
        logger.info(f"Fetching attendance data for device {device_name} (cloud_id: {cloud_id})")
        logger.debug(f"API URL: {url}, Data: {data}")
        
        try:
            # Make API request with POST method and JSON payload
            response_data = self._make_request('POST', url, device_config, json=data)
            
            if not response_data:
                logger.error(f"No response data from Fingerspot API for device {device_name}")
                return []
            
            # Check if request was successful
            if not response_data.get('success'):
                error_msg = response_data.get('message', 'Unknown API error')
                logger.warning(f"Fingerspot API returned error: {error_msg}")
                return []
            
            # Parse response data
            attendance_records = []
            
            # Handle different possible response formats
            if 'data' in response_data:
                records = response_data['data']
            elif 'attendance' in response_data:
                records = response_data['attendance']
            elif isinstance(response_data, list):
                records = response_data
            else:
                logger.warning(f"Unexpected response format from Fingerspot API: {response_data}")
                return []
            
            if not records:
                logger.info(f"No attendance records found for device {device_name}")
                return []
            
            # Convert to FingerspotAttendance objects
            for record in records:
                try:
                    # Parse timestamp
                    timestamp_str = record.get('scan_date') or record.get('datetime') or record.get('timestamp')
                    if timestamp_str:
                        timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                    else:
                        logger.warning(f"No timestamp found in record: {record}")
                        continue
                    
                    # Get user ID
                    user_id = record.get('pin') or record.get('user_id') or record.get('uid')
                    if not user_id:
                        logger.warning(f"No user ID found in record: {record}")
                        continue
                    
                    # Get punch/status code
                    punch = record.get('status') or record.get('punch') or record.get('verify')
                    if punch is None:
                        logger.warning(f"No punch/status found in record: {record}")
                        continue
                    
                    # Create attendance object
                    attendance = FingerspotAttendance(
                        user_id=str(user_id),
                        timestamp=timestamp,
                        punch=int(punch),
                        uid=record.get('uid')
                    )
                    
                    attendance_records.append(attendance)
                    
                except (ValueError, KeyError) as e:
                    logger.error(f"Error parsing attendance record {record}: {e}")
                    continue
            
            logger.info(f"Successfully parsed {len(attendance_records)} attendance records for device {device_name}")
            return attendance_records
            
        except Exception as e:
            logger.error(f"Error getting attendance data for device {device_name}: {str(e)}")
            return []

    def sync_device_data(self, device_config: Dict, start_date: datetime = None, end_date: datetime = None) -> Tuple[bool, str, List[Dict]]:
        """
        Sync attendance data from Fingerspot API and convert to FPLog format
        
        Args:
            device_config: Device configuration
            start_date: Start date for sync
            end_date: End date for sync
            
        Returns:
            Tuple of (success, message, fplog_data_list)
        """
        device_name = device_config.get('name')
        
        try:
            # Get attendance data from API
            attendance_records = self.get_attendance_data(device_config, start_date, end_date)
            
            if not attendance_records:
                return True, f"No attendance data found for device {device_name}", []
            
            # Convert to FPLog format
            fplog_data = []
            for att in attendance_records:
                # Determine device status using config logic
                device_status = determine_status(att.punch)
                status_display = get_status_display(device_status)
                
                # Create FPLog entry
                fplog_entry = {
                    'PIN': att.user_id,
                    'Date': att.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    'Machine': device_name,
                    'Status': device_status,  # Use converted status, not punch code
                    'fpid': None  # Will be filled later by sync process
                }
                
                fplog_data.append(fplog_entry)
                
                logger.debug(f"Converted record: PIN={att.user_id}, Status={device_status} ({status_display}), Time={att.timestamp}")
            
            logger.info(f"Successfully converted {len(fplog_data)} records for device {device_name}")
            return True, f"Successfully synced {len(fplog_data)} records", fplog_data
            
        except Exception as e:
            error_msg = f"Error syncing Fingerspot device {device_name}: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, []

    def get_device_info(self, device_config: Dict) -> Optional[Dict]:
        """
        Get device information from Fingerspot API
        
        Args:
            device_config: Device configuration
            
        Returns:
            Device information dict or None if failed
        """
        device_name = device_config.get('name')
        api_config = device_config.get('api_config', {})
        
        if not api_config:
            logger.error(f"No API config found for device {device_name}")
            return None
        
        # Build API URL
        base_url = api_config.get('base_url', self.base_config['base_url'])
        cloud_id = api_config.get('cloud_id')
        endpoint = self.base_config['endpoints']['devices']
        
        url = f"{base_url}{endpoint}"
        
        # Prepare request data
        data = {
            'trans_id': 1,
            'cloud_id': cloud_id
        }
        
        try:
            logger.info(f"Getting device info for {device_name}")
            response_data = self._make_request('POST', url, device_config, json=data)
            
            if response_data and response_data.get('success'):
                return response_data.get('data')
            else:
                error_msg = response_data.get('message', 'Unknown error') if response_data else 'No response'
                logger.error(f"Failed to get device info for {device_name}: {error_msg}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting device info for {device_name}: {str(e)}")
            return None
