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
                          pins: List[str] = None, limit: int = 1000) -> List[Dict[str, Any]]:
        """Get AttRecord data from database"""
        try:
            conn = self.db_manager.get_sqlserver_connection()
            if not conn:
                logger.error("Cannot get database connection")
                return []
            
            cursor = conn.cursor()
            
            # Build query with filters
            query = """
                SELECT 
                    pin,
                    tanggal,
                    jam_masuk,
                    jam_keluar,
                    status_absen,
                    jam_kerja,
                    terlambat,
                    lebih_awal,
                    lembur,
                    created_date,
                    modified_date
                FROM attrecord
                WHERE 1=1
            """
            
            params = []
            
            # Add date filter
            if start_date and end_date:
                query += " AND tanggal BETWEEN ? AND ?"
                params.extend([start_date, end_date])
            elif start_date:
                query += " AND tanggal >= ?"
                params.append(start_date)
            elif end_date:
                query += " AND tanggal <= ?"
                params.append(end_date)
            
            # Add PIN filter
            if pins and len(pins) > 0:
                placeholders = ','.join('?' * len(pins))
                query += f" AND pin IN ({placeholders})"
                params.extend(pins)
            
            # Add ordering and limit
            query += " ORDER BY tanggal DESC, pin"
            if limit:
                query = f"SELECT TOP {limit} * FROM ({query}) AS subquery"
            
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
    
    def push_data_to_vps(self, data: List[Dict[str, Any]], 
                        endpoint: str = None) -> Tuple[bool, str]:
        """Push data to VPS server"""
        if not self.push_enabled:
            return False, "VPS push service is disabled"
        
        if not data:
            return False, "No data to push"
        
        # Use custom endpoint or default
        url = endpoint or self.api_url
        
        # Prepare payload
        payload = {
            'data': data,
            'timestamp': datetime.now().isoformat(),
            'source': 'attendance_system',
            'record_count': len(data)
        }
        
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
                logger.info(f"Pushing {len(data)} records to VPS (attempt {attempt}/{self.retry_count})")
                
                response = requests.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=self.timeout,
                    verify=True  # Verify SSL certificates
                )
                
                # Check response
                if response.status_code == 200:
                    logger.info(f"Successfully pushed {len(data)} records to VPS")
                    return True, f"Successfully pushed {len(data)} records"
                
                elif response.status_code == 401:
                    logger.error("VPS API authentication failed - check API key")
                    return False, "Authentication failed"
                
                elif response.status_code == 429:
                    logger.warning("VPS API rate limit exceeded - retrying after delay")
                    if attempt < self.retry_count:
                        time.sleep(2 ** attempt)  # Exponential backoff
                        continue
                    return False, "Rate limit exceeded"
                
                else:
                    logger.warning(f"VPS API returned status {response.status_code}: {response.text}")
                    if attempt < self.retry_count:
                        time.sleep(1)
                        continue
                    return False, f"API error: {response.status_code}"
            
            except requests.exceptions.Timeout:
                logger.warning(f"VPS API timeout (attempt {attempt}/{self.retry_count})")
                if attempt < self.retry_count:
                    time.sleep(2)
                    continue
                return False, "Request timeout"
            
            except requests.exceptions.ConnectionError:
                logger.warning(f"VPS API connection error (attempt {attempt}/{self.retry_count})")
                if attempt < self.retry_count:
                    time.sleep(3)
                    continue
                return False, "Connection error"
            
            except Exception as e:
                logger.error(f"Unexpected error pushing to VPS: {e}")
                if attempt < self.retry_count:
                    time.sleep(2)
                    continue
                return False, f"Unexpected error: {str(e)}"
        
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
            
            # Push to VPS
            success, message = self.push_data_to_vps(data)
            
            if success:
                logger.info(f"Successfully pushed AttRecord data: {message}")
            else:
                logger.error(f"Failed to push AttRecord data: {message}")
            
            return success, message
            
        except Exception as e:
            logger.error(f"Error in push_attrecord_by_date_range: {e}")
            return False, f"Error: {str(e)}"
    
    def push_attrecord_today(self, pins: List[str] = None) -> Tuple[bool, str]:
        """Push today's AttRecord data"""
        today = datetime.now().strftime('%Y-%m-%d')
        return self.push_attrecord_by_date_range(today, today, pins)
    
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

# Global VPS push service instance
vps_push_service = VPSPushService()