"""
VPS Push Service untuk AttRecord Data
Service untuk mengirim data AttRecord ke VPS server
"""

import json
import requests
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from config.database import db_manager
from config.config import Config
from config.logging_config import get_background_logger

# Setup logging
logger = get_background_logger('VPSPushService', 'logs/vps_push_service.log')

class VPSPushService:
    """Service untuk mengirim data AttRecord ke VPS"""
    
    def __init__(self):
        self.db_manager = db_manager
        self.config = Config()
        
        # VPS API Configuration
        self.api_url = self.config.VPS_API_URL
        self.api_key = self.config.VPS_API_KEY
        self.timeout = self.config.VPS_API_TIMEOUT
        self.retry_count = self.config.VPS_API_RETRY_COUNT
        self.push_enabled = self.config.VPS_PUSH_ENABLED
        
        # Validate configuration
        self._validate_config()
    
    def _validate_config(self):
        """Validate VPS configuration"""
        if not self.push_enabled:
            logger.info("VPS push service is disabled")
            return
        
        if not self.api_url:
            logger.warning("VPS_API_URL not configured - VPS push will be disabled")
            self.push_enabled = False
            return
        
        if not self.api_key:
            logger.warning("VPS_API_KEY not configured - VPS push will be disabled")
            self.push_enabled = False
            return
        
        logger.info(f"VPS push service initialized - URL: {self.api_url}")
    
    def get_attrecord_data(self, start_date: str = None, end_date: str = None, 
                          pins: List[str] = None, limit: int = 5000) -> List[Dict[str, Any]]:
        """Get AttRecord data from database"""
        try:
            conn = self.db_manager.get_sqlserver_connection()
            if not conn:
                logger.error("Cannot get database connection")
                return []
            
            cursor = conn.cursor()
            
            # Build query with filters - use TOP with ORDER BY directly
            if limit:
                query = f"SELECT TOP {limit} * FROM attrecords WHERE 1=1"
            else:
                query = "SELECT * FROM attrecords WHERE 1=1"
            
            params = []
            
            # Add date filter
            if start_date and end_date:
                query += " AND tgl BETWEEN ? AND ?"
                params.extend([start_date, end_date])
            elif start_date:
                query += " AND tgl >= ?"
                params.append(start_date)
            elif end_date:
                query += " AND tgl <= ?"
                params.append(end_date)
            
            # Add PIN filter
            if pins and len(pins) > 0:
                placeholders = ','.join('?' * len(pins))
                query += f" AND pin IN ({placeholders})"
                params.extend(pins)
            
            # Add ordering - this works with TOP
            query += " ORDER BY tgl DESC, pin"
            
            cursor.execute(query, params)
            
            # Convert to list of dictionaries
            columns = [column[0] for column in cursor.description]
            rows = cursor.fetchall()
            
            data = []
            for row in rows:
                row_dict = {}
                for i, value in enumerate(row):
                    column_name = columns[i]
                    
                    # Handle different data types
                    if value is None:
                        row_dict[column_name] = None
                    elif hasattr(value, 'strftime'):  # datetime objects
                        if 'jam' in column_name.lower() and hasattr(value, 'time'):
                            # For time fields, just get time part
                            row_dict[column_name] = value.strftime('%H:%M:%S')
                        else:
                            # For date/datetime fields
                            row_dict[column_name] = value.strftime('%Y-%m-%d %H:%M:%S')
                    elif hasattr(value, 'total_seconds'):  # timedelta objects
                        # Convert timedelta to total minutes
                        row_dict[column_name] = int(value.total_seconds() / 60)
                    else:
                        row_dict[column_name] = str(value)
                
                data.append(row_dict)
            
            cursor.close()
            conn.close()
            
            logger.info(f"Retrieved {len(data)} AttRecord records from database")
            return data
            
        except Exception as e:
            logger.error(f"Error retrieving AttRecord data: {e}")
            return []
    
    def push_data_to_vps(self, data: List[Dict[str, Any]], endpoint: str = None) -> Tuple[bool, str]:
        """Push data to VPS server"""
        if not self.push_enabled:
            return False, "VPS push service is disabled"
        
        if not data:
            return False, "No data to push"
        
        # Transform data to match required format
        formatted_records = []
        for record in data:
            # Helper function to extract time from datetime string
            def extract_time(datetime_str):
                if not datetime_str or datetime_str is None:
                    return None
                try:
                    # Handle various datetime formats and extract time part
                    datetime_str = str(datetime_str).strip()
                    if ' ' in datetime_str:
                        # If contains space, take the time part after space
                        time_part = datetime_str.split(' ')[1]
                        # Ensure it's in HH:MM:SS format
                        if len(time_part.split(':')) == 3:
                            return time_part
                        elif len(time_part.split(':')) == 2:
                            return time_part + ':00'
                    elif ':' in datetime_str and len(datetime_str) <= 8:
                        # Already time format
                        if len(datetime_str.split(':')) == 2:
                            return datetime_str + ':00'
                        return datetime_str
                    return None
                except:
                    return None
            
            formatted_record = {
                "id": record.get('id'),
                "tgl": record.get('tgl')[:10] if record.get('tgl') else None,
                "fpid": record.get('fpid'),
                "pin": record.get('pin'),
                "name": record.get('name'),
                "jabatan": record.get('jabatan'),
                "lokasi": record.get('lokasi'),
                "deptname": record.get('deptname'),
                "masuk": extract_time(record.get('masuk')),
                "keluar": extract_time(record.get('keluar')),
                "shift": record.get('shift'),
                "created_at": record.get('created_at'),
                "updated_at": record.get('updated_at'),
                "keterangan": record.get('keterangan'),
                "masuk_produksi": extract_time(record.get('masuk_produksi')),
                "keluar_produksi": extract_time(record.get('keluar_produksi'))
            }
            formatted_records.append(formatted_record)
        
        # Prepare payload with the requested format
        payload = {
            "records": formatted_records
        }
        
        # Log payload to terminal and file
        print("\n" + "="*80)
        print("VPS PUSH PAYLOAD LOG")
        print("="*80)
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Total Records: {len(formatted_records)}")
        print(f"Target URL: {endpoint}")
        print("\nPayload JSON:")
        print(json.dumps(payload, indent=2, ensure_ascii=False, default=str))
        print("="*80 + "\n")
        
        # Also log to file
        logger.info(f"VPS Push Payload - Records: {len(formatted_records)}")
        logger.info(f"Payload JSON: {json.dumps(payload, ensure_ascii=False, default=str)}")
        
        # Prepare headers
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}',
            'X-API-Key': self.api_key,
            'User-Agent': 'AttendanceSystem/1.0'
        }
        
        # Log headers (without sensitive data)
        safe_headers = {k: v if k not in ['Authorization', 'X-API-Key'] else '***' for k, v in headers.items()}
        print(f"Request Headers: {json.dumps(safe_headers, indent=2)}")
        print("Starting VPS push operation...\n")
        
        # Attempt to push with retry logic
        for attempt in range(1, self.retry_count + 1):
            try:
                print(f"📤 Attempt {attempt}/{self.retry_count}: Pushing {len(data)} records to VPS...")
                logger.info(f"Pushing {len(data)} records to VPS (attempt {attempt}/{self.retry_count})")
                
                response = requests.post(
                    endpoint,
                    json=payload,
                    headers=headers,
                    timeout=self.timeout,
                    verify=True  # Verify SSL certificates
                )
                
                # Log response details
                print(f"📨 Response received: Status {response.status_code}")
                print(f"Response Headers: {dict(response.headers)}")
                print(f"Response Content: {response.text[:500]}{'...' if len(response.text) > 500 else ''}")
                
                # Check response
                if response.status_code == 200:
                    print("✅ SUCCESS: Data pushed successfully!")
                    logger.info(f"Successfully pushed {len(data)} records to VPS")
                    logger.info(f"VPS Response: {response.text}")
                    return True, f"Successfully pushed {len(data)} records"
                
                elif response.status_code == 401:
                    print("❌ AUTHENTICATION FAILED")
                    logger.error("VPS API authentication failed - check API key")
                    return False, "Authentication failed"
                
                elif response.status_code == 429:
                    print("⏳ RATE LIMIT EXCEEDED - retrying after delay...")
                    logger.warning("VPS API rate limit exceeded - retrying after delay")
                    if attempt < self.retry_count:
                        time.sleep(2 ** attempt)  # Exponential backoff
                        continue
                    return False, "Rate limit exceeded"
                
                else:
                    print(f"⚠️ API ERROR: Status {response.status_code}")
                    logger.warning(f"VPS API returned status {response.status_code}: {response.text}")
                    if attempt < self.retry_count:
                        print(f"Retrying in 1 second...")
                        time.sleep(1)
                        continue
                    return False, f"API error: {response.status_code}"
            
            except requests.exceptions.Timeout:
                print("⏰ REQUEST TIMEOUT")
                logger.warning(f"VPS API timeout (attempt {attempt}/{self.retry_count})")
                if attempt < self.retry_count:
                    print(f"Retrying in 2 seconds...")
                    time.sleep(2)
                    continue
                return False, "Request timeout"
            
            except requests.exceptions.ConnectionError:
                print("🔌 CONNECTION ERROR")
                logger.warning(f"VPS API connection error (attempt {attempt}/{self.retry_count})")
                if attempt < self.retry_count:
                    print(f"Retrying in 3 seconds...")
                    time.sleep(3)
                    continue
                return False, "Connection error"
            
            except Exception as e:
                print(f"💥 UNEXPECTED ERROR: {str(e)}")
                logger.error(f"Unexpected error pushing to VPS: {e}")
                if attempt < self.retry_count:
                    print(f"Retrying in 2 seconds...")
                    time.sleep(2)
                    continue
                return False, f"Unexpected error: {str(e)}"
        
        print("❌ ALL RETRY ATTEMPTS FAILED")
        return False, "All retry attempts failed"
    
    def push_attrecord_by_date_range(self, start_date: str, end_date: str, 
                                   pins: List[str] = None) -> Tuple[bool, str]:
        """Push AttRecord data by date range"""
        try:
            logger.info(f"Pushing AttRecord data for date range {start_date} to {end_date}")
            
            # Get data from database
            data = self.get_attrecord_data(start_date, end_date, pins)
            
            if not data:
                return False, "No AttRecord data found for the specified criteria"
            
            # Push to VPS - use simpler endpoint path
            endpoint = f"{self.api_url}/attendance/bulk-save" if not self.api_url.endswith('/attendance/bulk-save') else self.api_url

            success, message = self.push_data_to_vps(data, endpoint)

            if success:
                logger.info(f"Successfully pushed AttRecord data: {message}")
            else:
                logger.error(f"Failed to push AttRecord data: {message}")
            
            return success, message
            
        except Exception as e:
            logger.error(f"Error in push_attrecord_by_date_range: {e}")
            return False, f"Error: {str(e)}"
    
    def push_attrecord_today(self) -> Tuple[bool, str]:
        """Push today's AttRecord data"""
        today = datetime.now().strftime('%Y-%m-%d')
        return self.push_attrecord_by_date_range(today, today)

    def push_attrecord_for_pins(self, pins: List[str],
                              days_back: int = 7) -> Tuple[bool, str]:
        """Push AttRecord data for specific PINs"""
        try:
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
            
            return self.push_attrecord_by_date_range(start_date, end_date, pins)
            
        except Exception as e:
            logger.error(f"Error in push_attrecord_for_pins: {e}")
            return False, f"Error: {str(e)}"
    
    def test_vps_connection(self) -> Tuple[bool, str]:
        """Test connection to VPS API"""
        if not self.push_enabled:
            return False, "VPS push service is disabled"
        
        try:
            # Test with a simple ping or health check
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'X-API-Key': self.api_key,
                'User-Agent': 'AttendanceSystem/1.0'
            }
            
            # Try to ping the API (adjust endpoint as needed)
            test_url = self.api_url.replace('/attrecords', '/health') if '/attrecords' in self.api_url else f"{self.api_url}/health"
            
            response = requests.get(
                test_url,
                headers=headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                return True, "VPS API connection successful"
            else:
                return False, f"VPS API returned status {response.status_code}"
        
        except requests.exceptions.Timeout:
            return False, "Connection timeout"
        except requests.exceptions.ConnectionError:
            return False, "Connection error"
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    def get_push_statistics(self) -> Dict[str, Any]:
        """Get statistics about VPS push operations"""
        return {
            'push_enabled': self.push_enabled,
            'api_url': self.api_url if self.push_enabled else 'Not configured',
            'timeout': self.timeout,
            'retry_count': self.retry_count,
            'last_check': datetime.now().isoformat()
        }
    
    def get_sample_payload(self, start_date: str = None, end_date: str = None, 
                          pins: List[str] = None, limit: int = 2) -> Dict[str, Any]:
        """Get sample payload format for testing"""
        try:
            # Get sample data from database
            sample_data = self.get_attrecord_data(start_date, end_date, pins, limit)
            
            if not sample_data:
                return {
                    "records": [],
                    "message": "No data found for the specified criteria"
                }
            
            # Transform data to match required format
            formatted_records = []
            for record in sample_data:
                # Helper function to extract time from datetime string
                def extract_time(datetime_str):
                    if not datetime_str or datetime_str is None:
                        return None
                    try:
                        # Handle various datetime formats and extract time part
                        datetime_str = str(datetime_str).strip()
                        if ' ' in datetime_str:
                            # If contains space, take the time part after space
                            time_part = datetime_str.split(' ')[1]
                            # Ensure it's in HH:MM:SS format
                            if len(time_part.split(':')) == 3:
                                return time_part
                            elif len(time_part.split(':')) == 2:
                                return time_part + ':00'
                        elif ':' in datetime_str and len(datetime_str) <= 8:
                            # Already time format
                            if len(datetime_str.split(':')) == 2:
                                return datetime_str + ':00'
                            return datetime_str
                        return None
                    except:
                        return None
                
                formatted_record = {
                    "id": record.get('id'),
                    "tgl": record.get('tgl')[:10] if record.get('tgl') else None,
                    "fpid": record.get('fpid'),
                    "pin": record.get('pin'),
                    "name": record.get('name'),
                    "jabatan": record.get('jabatan'),
                    "lokasi": record.get('lokasi'),
                    "deptname": record.get('deptname'),
                    "masuk": extract_time(record.get('masuk')),
                    "keluar": extract_time(record.get('keluar')),
                    "shift": record.get('shift'),
                    "created_at": record.get('created_at'),
                    "updated_at": record.get('updated_at'),
                    "keterangan": record.get('keterangan'),
                    "masuk_produksi": extract_time(record.get('masuk_produksi')),
                    "keluar_produksi": extract_time(record.get('keluar_produksi'))
                }
                formatted_records.append(formatted_record)
            
            return {
                "records": formatted_records
            }
            
        except Exception as e:
            logger.error(f"Error generating sample payload: {e}")
            return {
                "records": [],
                "error": f"Error: {str(e)}"
            }
    
    def test_payload_logging(self, start_date: str = None, end_date: str = None, 
                           pins: List[str] = None, limit: int = 5):
        """Test method specifically for logging payload to terminal"""
        print("\n" + "🧪 " + "="*70)
        print("TEST PAYLOAD LOGGING")
        print("="*72)
        
        try:
            # Get sample data
            print(f"📊 Fetching sample data...")
            print(f"   Start Date: {start_date or 'Not specified'}")
            print(f"   End Date: {end_date or 'Not specified'}")
            print(f"   PINs: {pins or 'All PINs'}")
            print(f"   Limit: {limit}")
            
            sample_payload = self.get_sample_payload(start_date, end_date, pins, limit)
            
            print(f"\n📝 SAMPLE PAYLOAD:")
            print(json.dumps(sample_payload, indent=2, ensure_ascii=False, default=str))
            
            print(f"\n📊 PAYLOAD STATISTICS:")
            print(f"   Total Records: {len(sample_payload.get('records', []))}")
            print(f"   Payload Size: {len(json.dumps(sample_payload))} characters")
            
            if sample_payload.get('records'):
                first_record = sample_payload['records'][0]
                print(f"   Sample Fields: {list(first_record.keys())}")
                print(f"   Non-null Fields in First Record: {sum(1 for v in first_record.values() if v is not None)}")
            
            print("\n✅ Payload test completed successfully!")
            
        except Exception as e:
            print(f"❌ Error in payload test: {str(e)}")
            
        print("="*72 + "\n")

    def get_workinghours_data(self, start_date: str = None, end_date: str = None, 
                              pins: List[str] = None, limit: int = 5000) -> List[Dict[str, Any]]:
        """Get WorkingHours data from database"""
        try:
            conn = self.db_manager.get_sqlserver_connection()
            if not conn:
                logger.error("Cannot get database connection")
                return []
            
            cursor = conn.cursor()
            
            # Build query with filters - use correct column name: working_date
            if limit:
                query = f"SELECT TOP {limit} * FROM workinghourrecs WHERE 1=1"
            else:
                query = "SELECT * FROM workinghourrecs WHERE 1=1"
            
            params = []
            
            # Add date filter - use working_date column
            if start_date and end_date:
                query += " AND working_date BETWEEN ? AND ?"
                params.extend([start_date, end_date])
            elif start_date:
                query += " AND working_date >= ?"
                params.append(start_date)
            elif end_date:
                query += " AND working_date <= ?"
                params.append(end_date)
            
            # Add PIN filter
            if pins and len(pins) > 0:
                placeholders = ','.join('?' * len(pins))
                query += f" AND pin IN ({placeholders})"
                params.extend(pins)
            
            # Add ordering - use working_date column
            query += " ORDER BY working_date DESC, pin"
            
            cursor.execute(query, params)
            
            # Convert to list of dictionaries
            columns = [column[0] for column in cursor.description]
            rows = cursor.fetchall()
            
            data = []
            for row in rows:
                row_dict = {}
                for i, value in enumerate(row):
                    column_name = columns[i]
                    
                    # Handle different data types
                    if value is None:
                        row_dict[column_name] = None
                    elif hasattr(value, 'strftime'):  # datetime objects
                        # Check if it's a time field
                        if any(time_field in column_name.lower() for time_field in ['masuk', 'keluar', 'break_out', 'break_in']):
                            # For time fields, just get time part
                            row_dict[column_name] = value.strftime('%H:%M:%S')
                        else:
                            # For date/datetime fields
                            row_dict[column_name] = value.strftime('%Y-%m-%d %H:%M:%S') if hasattr(value, 'hour') else value.strftime('%Y-%m-%d')
                    elif hasattr(value, 'total_seconds'):  # timedelta objects
                        # Convert timedelta to total hours (as decimal)
                        row_dict[column_name] = round(value.total_seconds() / 3600, 2)
                    elif isinstance(value, (int, float)):
                        row_dict[column_name] = value
                    else:
                        row_dict[column_name] = str(value)
                
                data.append(row_dict)
            
            cursor.close()
            conn.close()
            
            logger.info(f"Retrieved {len(data)} WorkingHours records from database")
            return data
            
        except Exception as e:
            logger.error(f"Error retrieving WorkingHours data: {e}")
            return []
    
    def push_workinghours_by_date_range(self, start_date: str, end_date: str, 
                                        pins: List[str] = None) -> Tuple[bool, str]:
        """Push WorkingHours data by date range"""
        try:
            logger.info(f"Pushing WorkingHours data for date range {start_date} to {end_date}")
            
            # Get data from database
            data = self.get_workinghours_data(start_date, end_date, pins)
            
            if not data:
                return False, "No WorkingHours data found for the specified criteria"
            
            # Transform data to proper format with correct column names
            formatted_records = []
            for record in data:
                formatted_record = {
                    "id": record.get('id'),
                    "pin": record.get('pin'),
                    "name": record.get('name'),
                    "shift": record.get('shift'),
                    "shift_name": record.get('shift_name'),
                    "deptname": record.get('deptname'),
                    "location": record.get('location'),
                    "working_date": record.get('working_date')[:10] if record.get('working_date') else None,
                    "working_day": record.get('working_day'),
                    "check_in": record.get('check_in'),
                    "check_out": record.get('check_out'),
                    "check_in_production": record.get('check_in_production'),
                    "check_out_production": record.get('check_out_production'),
                    "break_out": record.get('break_out'),
                    "break_in": record.get('break_in'),
                    "break_time": record.get('break_time'),
                    "break_out_2": record.get('break_out_2'),
                    "break_in_2": record.get('break_in_2'),
                    "break_time_2": record.get('break_time_2'),
                    "workinghours": record.get('workinghours'),
                    "overtime": record.get('overtime'),
                    "workingdays": record.get('workingdays'),
                    "total_hours": record.get('total_hours'),
                    "created_at": record.get('created_at'),
                    "updated_at": record.get('updated_at')
                }
                formatted_records.append(formatted_record)
            
            # Prepare payload
            payload = {
                "records": formatted_records
            }
            
            # Log payload
            print("\n" + "="*80)
            print("VPS PUSH WORKINGHOURS PAYLOAD LOG")
            print("="*80)
            print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"Total Records: {len(formatted_records)}")
            print(f"Start Date: {start_date}")
            print(f"End Date: {end_date}")
            print("\nPayload JSON (first 2 records):")
            sample_payload = {"records": formatted_records[:2]}
            print(json.dumps(sample_payload, indent=2, ensure_ascii=False, default=str))
            print("="*80 + "\n")
            
            logger.info(f"WorkingHours Push Payload - Records: {len(formatted_records)}")
            
            # Push to VPS
            endpoint = f"{self.api_url}/workinghours/bulk-upsert" if not self.api_url.endswith('/workinghours/bulk-upsert') else self.api_url
            
            # Prepare headers
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.api_key}',
                'X-API-Key': self.api_key,
                'User-Agent': 'AttendanceSystem/1.0'
            }
            
            # Attempt to push with retry logic
            for attempt in range(1, self.retry_count + 1):
                try:
                    print(f"📤 Attempt {attempt}/{self.retry_count}: Pushing {len(data)} WorkingHours records to VPS...")
                    logger.info(f"Pushing {len(data)} WorkingHours records to VPS (attempt {attempt}/{self.retry_count})")
                    
                    response = requests.post(
                        endpoint,
                        json=payload,
                        headers=headers,
                        timeout=self.timeout,
                        verify=True
                    )
                    
                    print(f"📨 Response received: Status {response.status_code}")
                    
                    if response.status_code == 200:
                        print("✅ SUCCESS: WorkingHours data pushed successfully!")
                        logger.info(f"Successfully pushed {len(data)} WorkingHours records to VPS")
                        return True, f"Successfully pushed {len(data)} WorkingHours records"
                    
                    elif response.status_code == 401:
                        print("❌ AUTHENTICATION FAILED")
                        logger.error("VPS API authentication failed - check API key")
                        return False, "Authentication failed"
                    
                    elif response.status_code == 429:
                        print("⏳ RATE LIMIT EXCEEDED - retrying after delay...")
                        logger.warning("VPS API rate limit exceeded - retrying after delay")
                        if attempt < self.retry_count:
                            time.sleep(2 ** attempt)
                            continue
                        return False, "Rate limit exceeded"
                    
                    else:
                        print(f"⚠️ API ERROR: Status {response.status_code}")
                        logger.warning(f"VPS API returned status {response.status_code}: {response.text}")
                        if attempt < self.retry_count:
                            time.sleep(1)
                            continue
                        return False, f"API error: {response.status_code}"
                
                except requests.exceptions.Timeout:
                    print("⏰ REQUEST TIMEOUT")
                    if attempt < self.retry_count:
                        time.sleep(2)
                        continue
                    return False, "Request timeout"
                
                except requests.exceptions.ConnectionError:
                    print("🔌 CONNECTION ERROR")
                    if attempt < self.retry_count:
                        time.sleep(3)
                        continue
                    return False, "Connection error"
                
                except Exception as e:
                    print(f"💥 UNEXPECTED ERROR: {str(e)}")
                    if attempt < self.retry_count:
                        time.sleep(2)
                        continue
                    return False, f"Unexpected error: {str(e)}"
            
            return False, "All retry attempts failed"
            
        except Exception as e:
            logger.error(f"Error in push_workinghours_by_date_range: {e}")
            return False, f"Error: {str(e)}"
    
    def push_workinghours_today(self) -> Tuple[bool, str]:
        """Push WorkingHours data from yesterday to today"""
        today = datetime.now().strftime('%Y-%m-%d')
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        return self.push_workinghours_by_date_range(yesterday, today)
    
    def push_workinghours_for_pins(self, pins: List[str], days_back: int = 7) -> Tuple[bool, str]:
        """Push WorkingHours data for specific PINs"""
        try:
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
            
            return self.push_workinghours_by_date_range(start_date, end_date, pins)
            
        except Exception as e:
            logger.error(f"Error in push_workinghours_for_pins: {e}")
            return False, f"Error: {str(e)}"
    
    def get_workinghours_preview(self, start_date: str = None, end_date: str = None, 
                                 pins: List[str] = None, limit: int = 100) -> Dict[str, Any]:
        """Get preview of WorkingHours data format"""
        try:
            # Get sample data from database
            sample_data = self.get_workinghours_data(start_date, end_date, pins, limit)
            
            if not sample_data:
                return {
                    "records": [],
                    "message": "No WorkingHours data found for the specified criteria"
                }
            
            # Transform data to match required format with correct column names
            formatted_records = []
            for record in sample_data:
                formatted_record = {
                    "id": record.get('id'),
                    "pin": record.get('pin'),
                    "name": record.get('name'),
                    "shift": record.get('shift'),
                    "shift_name": record.get('shift_name'),
                    "deptname": record.get('deptname'),
                    "location": record.get('location'),
                    "working_date": record.get('working_date')[:10] if record.get('working_date') else None,
                    "working_day": record.get('working_day'),
                    "check_in": record.get('check_in'),
                    "check_out": record.get('check_out'),
                    "check_in_production": record.get('check_in_production'),
                    "check_out_production": record.get('check_out_production'),
                    "break_out": record.get('break_out'),
                    "break_in": record.get('break_in'),
                    "break_time": record.get('break_time'),
                    "break_out_2": record.get('break_out_2'),
                    "break_in_2": record.get('break_in_2'),
                    "break_time_2": record.get('break_time_2'),
                    "workinghours": record.get('workinghours'),
                    "overtime": record.get('overtime'),
                    "workingdays": record.get('workingdays'),
                    "total_hours": record.get('total_hours'),
                    "created_at": record.get('created_at'),
                    "updated_at": record.get('updated_at')
                }
                formatted_records.append(formatted_record)
            
            return {
                "records": formatted_records
            }
            
        except Exception as e:
            logger.error(f"Error generating WorkingHours preview: {e}")
            return {
                "records": [],
                "error": f"Error: {str(e)}"
            }
    
    # =========================================================================
    # FPLOG PUSH METHODS
    # =========================================================================
    
    def get_fplog_data(self, start_date: str = None, end_date: str = None, 
                       pins: List[str] = None, limit: int = 5000) -> List[Dict[str, Any]]:
        """Get FPLog data from database
        
        Args:
            start_date: Start date filter (YYYY-MM-DD format)
            end_date: End date filter (YYYY-MM-DD format)
            pins: List of employee PINs to filter
            limit: Maximum number of records to retrieve
            
        Returns:
            List of FPLog records as dictionaries
        """
        try:
            conn = self.db_manager.get_sqlserver_connection()
            if not conn:
                logger.error("Cannot get database connection for FPLog")
                return []
            
            cursor = conn.cursor()
            
            # Build query with filters
            if limit:
                query = f"SELECT TOP {limit} * FROM FPLog WHERE 1=1"
            else:
                query = "SELECT * FROM FPLog WHERE 1=1"
            
            params = []
            
            # Add date filter
            if start_date and end_date:
                query += " AND CAST(Date AS DATE) BETWEEN ? AND ?"
                params.extend([start_date, end_date])
            elif start_date:
                query += " AND CAST(Date AS DATE) >= ?"
                params.append(start_date)
            elif end_date:
                query += " AND CAST(Date AS DATE) <= ?"
                params.append(end_date)
            
            # Add PIN filter
            if pins and len(pins) > 0:
                placeholders = ','.join('?' * len(pins))
                query += f" AND PIN IN ({placeholders})"
                params.extend(pins)
            
            # Add ordering
            query += " ORDER BY Date DESC, PIN"
            
            logger.info(f"Executing FPLog query with filters - start_date: {start_date}, end_date: {end_date}, pins: {pins}, limit: {limit}")
            cursor.execute(query, params)
            
            # Convert to list of dictionaries
            columns = [column[0] for column in cursor.description]
            rows = cursor.fetchall()
            
            data = []
            for row in rows:
                row_dict = {}
                for i, value in enumerate(row):
                    # Convert datetime objects to string
                    if isinstance(value, datetime):
                        row_dict[columns[i]] = value.strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        row_dict[columns[i]] = value
                data.append(row_dict)
            
            cursor.close()
            conn.close()
            
            logger.info(f"Retrieved {len(data)} FPLog records from database")
            return data
            
        except Exception as e:
            logger.error(f"Error getting FPLog data: {e}")
            return []
    
    def push_fplog_by_date_range(self, start_date: str, end_date: str, 
                                 endpoint: str = '/fplog/bulk-upsert') -> Tuple[bool, str]:
        """Push FPLog data to VPS by date range
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            endpoint: VPS API endpoint (default: /fplog/bulk-upsert)
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        if not self.push_enabled:
            return False, "VPS push service is disabled"
        
        try:
            # Get data from database
            logger.info(f"Fetching FPLog data for date range: {start_date} to {end_date}")
            data = self.get_fplog_data(start_date=start_date, end_date=end_date)
            
            if not data:
                logger.warning(f"No FPLog data found for date range {start_date} to {end_date}")
                return False, "No data found for the specified date range"
            
            # Push to VPS
            return self._push_fplog_to_vps(data, endpoint)
            
        except Exception as e:
            logger.error(f"Error pushing FPLog by date range: {e}")
            return False, f"Error: {str(e)}"
    
    def push_fplog_today(self, endpoint: str = '/fplog/bulk-upsert') -> Tuple[bool, str]:
        """Push FPLog data for today (yesterday to today - 2 days)
        
        Args:
            endpoint: VPS API endpoint (default: /fplog/bulk-upsert)
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        yesterday = datetime.now() - timedelta(days=1)
        today = datetime.now()
        
        start_date = yesterday.date().isoformat()
        end_date = today.date().isoformat()
        
        logger.info(f"Pushing FPLog data for today (yesterday to today): {start_date} to {end_date}")
        return self.push_fplog_by_date_range(start_date, end_date, endpoint)
    
    def push_fplog_for_pins(self, pins: List[str], days_back: int = 7, 
                           endpoint: str = '/fplog/bulk-upsert') -> Tuple[bool, str]:
        """Push FPLog data for specific employee PINs
        
        Args:
            pins: List of employee PINs
            days_back: Number of days to look back (default: 7)
            endpoint: VPS API endpoint (default: /fplog/bulk-upsert)
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        if not self.push_enabled:
            return False, "VPS push service is disabled"
        
        if not pins or len(pins) == 0:
            return False, "No employee PINs provided"
        
        try:
            # Calculate date range
            end_date = datetime.now().date().isoformat()
            start_date = (datetime.now() - timedelta(days=days_back)).date().isoformat()
            
            # Get data from database
            logger.info(f"Fetching FPLog data for PINs: {pins}, date range: {start_date} to {end_date}")
            data = self.get_fplog_data(start_date=start_date, end_date=end_date, pins=pins)
            
            if not data:
                logger.warning(f"No FPLog data found for PINs: {pins}")
                return False, f"No data found for the specified PINs"
            
            # Push to VPS
            return self._push_fplog_to_vps(data, endpoint)
            
        except Exception as e:
            logger.error(f"Error pushing FPLog by PINs: {e}")
            return False, f"Error: {str(e)}"
    
    def _push_fplog_to_vps(self, data: List[Dict[str, Any]], 
                          endpoint: str = '/fplog/bulk-upsert') -> Tuple[bool, str]:
        """Internal method to push FPLog data to VPS
        
        Args:
            data: List of FPLog records
            endpoint: VPS API endpoint
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        if not data:
            return False, "No data to push"
        
        try:
            # Prepare request
            url = f"{self.api_url}{endpoint}"
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.api_key}',
                'X-API-Key': self.api_key
            }
            
            # Transform data to match VPS API format
            # Expected format: {FPID, PIN, date, Machine, status}
            formatted_records = []
            for record in data:
                formatted_record = {
                    "FPID": str(record.get('FPID', '')),
                    "PIN": str(record.get('PIN', '')),
                    "date": record.get('Date', ''),  # Already in 'YYYY-MM-DD HH:MM:SS' format
                    "Machine": str(record.get('Machine', '')),
                    "status": record.get('status')
                }
                formatted_records.append(formatted_record)
            
            # Format payload - send records array only
            payload = {
                'records': formatted_records
            }
            
            logger.info(f"Pushing {len(data)} FPLog records to VPS: {url}")
            
            # Try to push with retry logic
            for attempt in range(self.retry_count):
                try:
                    response = requests.post(
                        url,
                        json=payload,
                        headers=headers,
                        timeout=self.timeout
                    )
                    
                    if response.status_code == 200 or response.status_code == 201:
                        logger.info(f"Successfully pushed {len(data)} FPLog records to VPS")
                        return True, f"Successfully pushed {len(data)} FPLog records to VPS"
                    else:
                        error_msg = f"VPS returned status {response.status_code}: {response.text}"
                        logger.warning(f"Attempt {attempt + 1}/{self.retry_count} failed - {error_msg}")
                        
                        if attempt < self.retry_count - 1:
                            time.sleep(2 ** attempt)  # Exponential backoff
                            continue
                        else:
                            return False, error_msg
                            
                except requests.exceptions.Timeout:
                    logger.warning(f"Attempt {attempt + 1}/{self.retry_count} - Request timeout")
                    if attempt < self.retry_count - 1:
                        time.sleep(2 ** attempt)
                        continue
                    else:
                        return False, "Request timeout after multiple attempts"
                        
                except requests.exceptions.RequestException as e:
                    logger.warning(f"Attempt {attempt + 1}/{self.retry_count} - Request error: {e}")
                    if attempt < self.retry_count - 1:
                        time.sleep(2 ** attempt)
                        continue
                    else:
                        return False, f"Request error: {str(e)}"
            
            return False, "Failed to push data after all retry attempts"
            
        except Exception as e:
            logger.error(f"Error pushing FPLog to VPS: {e}")
            return False, f"Error: {str(e)}"
    
    def get_fplog_preview(self, start_date: str = None, end_date: str = None, 
                         pins: List[str] = None, limit: int = 50) -> Dict[str, Any]:
        """Get preview of FPLog data without pushing to VPS
        
        Args:
            start_date: Start date filter
            end_date: End date filter
            pins: List of employee PINs to filter
            limit: Maximum number of records (default: 50)
            
        Returns:
            Dictionary with preview data
        """
        try:
            # Get data from database
            data = self.get_fplog_data(
                start_date=start_date, 
                end_date=end_date, 
                pins=pins, 
                limit=limit
            )
            
            # Format for preview - same format as will be sent to VPS
            formatted_records = []
            for record in data:
                formatted_record = {
                    "FPID": str(record.get('fpid', '')),
                    "PIN": str(record.get('PIN', '')),
                    "date": record.get('Date', ''),
                    "Machine": str(record.get('Machine', '')),
                    "status": str(record.get('Status', '')) if record.get('Status') is not None else ''
                }
                formatted_records.append(formatted_record)
            
            return {
                "records": formatted_records
            }
            
        except Exception as e:
            logger.error(f"Error generating FPLog preview: {e}")
            return {
                "records": [],
                "error": f"Error: {str(e)}"
            }

# Global VPS push service instance
vps_push_service = VPSPushService()