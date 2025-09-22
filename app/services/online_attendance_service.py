"""
Service untuk mengambil data dari Online Attendance API dan menyimpannya ke tabel gagalabsens
"""
import requests
import logging
from datetime import datetime, timedelta
from config.database import db_manager
from config.devices import get_device_by_name, DEVICE_STATUS_RULES, ONLINE_ATTENDANCE_API_CONFIG

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OnlineAttendanceService:
    """Service untuk mengelola data absensi online dari API eksternal"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.device_config = get_device_by_name('Absensi Online')
        self.db_manager = db_manager
        self.api_config = ONLINE_ATTENDANCE_API_CONFIG
        self.base_url = self.api_config['base_url']
        self.headers = self.api_config['headers']
        self.timeout = self.api_config['timeout']
        
        if not self.device_config:
            raise ValueError("Device 'Absensi Online' tidak ditemukan dalam konfigurasi")
    
    def test_connection(self, device_config=None):
        """
        Test koneksi ke Online Attendance API
        
        Args:
            device_config (dict): Device configuration (optional, will use self.device_config if not provided)
            
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            # Gunakan device_config yang diberikan atau default
            config = device_config or self.device_config
            if not config:
                return False, "Device configuration tidak ditemukan"
            
            # Ambil konfigurasi API
            api_config = config.get('api_config', {})
            base_url = api_config.get('base_url', '')
            endpoint = api_config.get('endpoint', '')
            api_key = api_config.get('api_key', '')
            timeout = api_config.get('timeout', 30)
            
            if not base_url:
                return False, "Base URL tidak dikonfigurasi"
            
            if not endpoint:
                return False, "Endpoint tidak dikonfigurasi"
            
            # URL lengkap untuk test
            test_url = f"{base_url}{endpoint}"
            
            # Headers untuk request
            headers = self.headers.copy()
            if api_key:
                headers['Authorization'] = f'Bearer {api_key}'
            
            # Parameters untuk test - ambil data hari ini saja untuk test koneksi
            today = datetime.now().strftime('%Y-%m-%d')
            params = {
                'start_date': today,
                'end_date': today,
                'format': 'json',
                'limit': 1  # Hanya ambil 1 record untuk test
            }
            
            self.logger.info(f"Testing connection to {test_url}")
            
            # Lakukan request test
            response = requests.get(
                test_url,
                headers=headers,
                params=params,
                timeout=timeout
            )
            
            # Check status code
            if response.status_code == 200:
                try:
                    data = response.json()
                    # Validasi bahwa response dalam format yang diharapkan
                    if isinstance(data, (list, dict)):
                        return True, f"Koneksi berhasil ke {test_url}. Status: {response.status_code}"
                    else:
                        return False, f"Response format tidak dikenal: {type(data)}"
                except ValueError as e:
                    return False, f"Response bukan JSON valid: {str(e)}"
                    
            elif response.status_code == 401:
                return False, f"Unauthorized - API key mungkin tidak valid. Status: {response.status_code}"
            elif response.status_code == 403:
                return False, f"Forbidden - Akses ditolak. Status: {response.status_code}"
            elif response.status_code == 404:
                return False, f"Endpoint tidak ditemukan: {test_url}. Status: {response.status_code}"
            else:
                return False, f"API request gagal. Status: {response.status_code}, Response: {response.text[:200]}"
                
        except requests.exceptions.ConnectionError as e:
            return False, f"Koneksi gagal - Server tidak dapat dijangkau: {str(e)}"
        except requests.exceptions.Timeout as e:
            return False, f"Koneksi timeout setelah {timeout} detik: {str(e)}"
        except requests.exceptions.RequestException as e:
            return False, f"Request error: {str(e)}"
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"

    def fetch_attendance_data(self, start_date=None, end_date=None):
        """
        Mengambil data absensi dari API eksternal
        
        Args:
            start_date (str): Tanggal mulai dalam format YYYY-MM-DD
            end_date (str): Tanggal akhir dalam format YYYY-MM-DD
            
        Returns:
            tuple: (success: bool, data: list, message: str)
        """
        try:
            # Jika tidak ada tanggal yang ditentukan, ambil data 3 jam terakhir
            if not start_date or not end_date:
                end_time = datetime.now()
                start_time = end_time - timedelta(hours=3)
                start_date = start_time.strftime('%Y-%m-%d')
                end_date = end_time.strftime('%Y-%m-%d')
            
            # Konfigurasi API
            api_config = self.device_config['api_config']
            base_url = api_config['base_url']
            endpoint = api_config['endpoint']
            api_key = api_config.get('api_key', '')
            timeout = api_config.get('timeout', 30)
            
            # URL lengkap
            full_url = f"{base_url}{endpoint}"
            
            # Headers untuk request
            headers = self.headers.copy()
            if api_key:
                headers['Authorization'] = f'Bearer {api_key}'
                # atau headers['X-API-Key'] = api_key, sesuaikan dengan API
            
            # Parameters untuk request
            params = {
                'start_date': start_date,
                'end_date': end_date,
                'format': 'json'
            }
            
            self.logger.info(f"Fetching attendance data from {full_url}")
            self.logger.info(f"Date range: {start_date} to {end_date}")
            
            # Lakukan request ke API
            response = requests.get(
                full_url,
                headers=headers,
                params=params,
                timeout=timeout
            )
            
            # Check status code
            if response.status_code == 200:
                data = response.json()
                
                # Validasi struktur response
                if isinstance(data, dict):
                    # Jika response berupa dict dengan key 'data' atau 'results'
                    attendance_records = data.get('data', data.get('results', []))
                elif isinstance(data, list):
                    # Jika response langsung berupa list
                    attendance_records = data
                else:
                    return False, [], f"Format response tidak dikenal: {type(data)}"
                
                self.logger.info(f"Successfully fetched {len(attendance_records)} records")
                return True, attendance_records, f"Berhasil mengambil {len(attendance_records)} data"
                
            else:
                error_msg = f"API request failed with status {response.status_code}: {response.text}"
                self.logger.error(error_msg)
                return False, [], error_msg
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Request error: {str(e)}"
            self.logger.error(error_msg)
            return False, [], error_msg
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            self.logger.error(error_msg)
            return False, [], error_msg

    
    def process_attendance_record(self, record):
        """
        Memproses single record dan menentukan machine berdasarkan aturan device
        Status akan tetap menggunakan nilai asli dari API response tanpa konversi
        
        Args:
            record (dict): Data record dari API dengan format:
            {
                "pin": "8047",
                "status": "I",
                "created_at": "2025-09-17T07:32:39.000000Z"
            }
            
        Returns:
            dict: Processed record untuk disimpan ke gagalabsens
        """
        try:
            # Ekstrak data dari record API sesuai format response baru
            pin = str(record.get('pin', ''))
            status_raw = record.get('status', '')
            created_at = record.get('created_at', '')
            
            # Validasi PIN
            if not pin:
                raise ValueError("PIN tidak ditemukan dalam record")
            
            # Validasi status
            if not status_raw:
                raise ValueError("Status tidak ditemukan dalam record")
            
            # Validasi created_at
            if not created_at:
                raise ValueError("created_at tidak ditemukan dalam record")
            
            # Parse timestamp dari format ISO 8601 (2025-09-17T07:32:39.000000Z)
            try:
                # Handle format ISO 8601 dengan microseconds dan timezone Z
                if created_at.endswith('Z'):
                    # Remove Z and microseconds for parsing
                    timestamp_str = created_at.replace('Z', '').split('.')[0]
                    parsed_time = datetime.strptime(timestamp_str, '%Y-%m-%dT%H:%M:%S')
                else:
                    # Fallback untuk format lain
                    for fmt in ['%Y-%m-%dT%H:%M:%S.%fZ', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S']:
                        try:
                            parsed_time = datetime.strptime(created_at, fmt)
                            break
                        except ValueError:
                            continue
                    else:
                        raise ValueError(f"Format timestamp tidak dikenal: {created_at}")
                
                # Convert ke format database (YYYY-MM-DD HH:MM:SS)
                timestamp = parsed_time.strftime('%Y-%m-%d %H:%M:%S')
                
            except Exception as e:
                raise ValueError(f"Error parsing timestamp '{created_at}': {e}")
            
            # Tentukan machine berdasarkan aturan device, tapi TETAP GUNAKAN STATUS ASLI
            device_rules = DEVICE_STATUS_RULES.get('Absensi Online', {})
            
            # Mapping status dari API ke machine number, STATUS TETAP ASLI
            if status_raw == 'I':
                machine = device_rules.get('I', '114')  # Default machine untuk masuk
            elif status_raw == 'O':
                machine = device_rules.get('O', '112')  # Default machine untuk keluar
            else:
                # Untuk status lain yang tidak dikenal
                machine = device_rules.get('punch_other', '112')  # Default machine
            
            # Return processed record dengan STATUS ASLI dari API
            processed_record = {
                'pin': pin,
                'tgl': timestamp,
                'machine': machine,
                'status': status_raw,  # GUNAKAN STATUS ASLI DARI API (I/O)
                'raw_data': record  # Simpan data mentah untuk debugging
            }
            
            self.logger.debug(f"Processed record: PIN={pin}, Status={status_raw} (original), Time={timestamp}, Machine={machine}")
            return processed_record
            
        except Exception as e:
            self.logger.error(f"Error processing record: {e}")
            self.logger.error(f"Record data: {record}")
            raise
    
    def save_to_gagalabsens(self, records):
        """
        Menyimpan data ke tabel gagalabsens
        
        Args:
            records (list): List of processed records
            
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            if not records:
                return True, "Tidak ada data untuk disimpan"
            
            conn = self.db_manager.get_sqlserver_connection()
            if not conn:
                return False, "Gagal koneksi ke database"
            
            cursor = conn.cursor()
            
            # Query untuk insert
            insert_query = """
                INSERT INTO gagalabsens (pin, tgl, machine, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, GETDATE(), GETDATE())
            """
            
            # Prepare batch values
            batch_values = []
            for record in records:
                batch_values.append((
                    record['pin'],
                    record['tgl'],
                    record['machine'],
                    record['status']
                ))
            
            # Execute batch insert
            cursor.executemany(insert_query, batch_values)
            inserted_count = cursor.rowcount
            
            conn.commit()
            cursor.close()
            conn.close()
            
            success_msg = f"Berhasil menyimpan {inserted_count} record ke tabel gagalabsens"
            self.logger.info(success_msg)
            return True, success_msg
            
        except Exception as e:
            error_msg = f"Error saving to gagalabsens: {str(e)}"
            self.logger.error(error_msg)
            try:
                if 'cursor' in locals():
                    cursor.close()
                if 'conn' in locals():
                    conn.close()
            except:
                pass
            return False, error_msg
    
    def check_duplicate_in_gagalabsens(self, pin, timestamp, machine):
        """
        Cek apakah record sudah ada di tabel gagalabsens
        
        Args:
            pin (str): PIN karyawan
            timestamp (str): Timestamp dalam format YYYY-MM-DD HH:MM:SS
            machine (str): Machine identifier
            
        Returns:
            bool: True jika duplicate ditemukan
        """
        try:
            conn = self.db_manager.get_sqlserver_connection()
            if not conn:
                return False
            
            cursor = conn.cursor()
            
            # Check untuk duplicate berdasarkan PIN, timestamp (down to minute), dan machine
            check_query = """
                SELECT COUNT(*) as count
                FROM gagalabsens
                WHERE pin = ? 
                AND CONVERT(varchar(16), tgl, 120) = CONVERT(varchar(16), ?, 120)
                AND machine = ?
            """
            
            cursor.execute(check_query, (pin, timestamp, machine))
            result = cursor.fetchone()
            count = result[0] if result else 0
            
            cursor.close()
            conn.close()
            
            return count > 0
            
        except Exception as e:
            self.logger.error(f"Error checking duplicate: {e}")
            return False
    
    def filter_duplicates(self, records):
        """
        Filter out duplicate records
        
        Args:
            records (list): List of processed records
            
        Returns:
            list: Filtered records without duplicates
        """
        filtered_records = []
        
        for record in records:
            try:
                is_duplicate = self.check_duplicate_in_gagalabsens(
                    record['pin'],
                    record['tgl'],
                    record['machine']
                )
                
                if not is_duplicate:
                    filtered_records.append(record)
                else:
                    self.logger.debug(f"Skipping duplicate record: PIN={record['pin']}, Time={record['tgl']}")
                    
            except Exception as e:
                self.logger.error(f"Error checking duplicate for record: {e}")
                # Jika ada error, skip record ini untuk keamanan
                continue
        
        return filtered_records
    
    def sync_attendance_data(self, start_date=None, end_date=None):
        """
        Main method untuk melakukan sync data absensi dari API ke gagalabsens
        
        Args:
            start_date (str): Tanggal mulai (optional)
            end_date (str): Tanggal akhir (optional)
            
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            self.logger.info("Starting online attendance data sync")
            
            # Step 1: Fetch data from API
            success, raw_data, fetch_message = self.fetch_attendance_data(start_date, end_date)
            
            if not success:
                return False, f"Failed to fetch data: {fetch_message}"
            
            if not raw_data:
                return True, "No new data available from API"
            
            # Step 2: Process raw data
            processed_records = []
            processing_errors = []
            
            for record in raw_data:
                try:
                    processed_record = self.process_attendance_record(record)
                    processed_records.append(processed_record)
                except Exception as e:
                    processing_errors.append(f"Error processing record: {e}")
                    continue
            
            if not processed_records:
                error_msg = "No valid records after processing"
                if processing_errors:
                    error_msg += f". Errors: {'; '.join(processing_errors[:3])}"
                return False, error_msg
            
            # Step 3: Filter duplicates
            filtered_records = self.filter_duplicates(processed_records)
            
            if not filtered_records:
                return True, f"All {len(processed_records)} records were duplicates - no new data to save"
            
            # Step 4: Save to database
            save_success, save_message = self.save_to_gagalabsens(filtered_records)
            
            if not save_success:
                return False, f"Failed to save data: {save_message}"
            
            # Step 5: Return summary
            summary_msg = f"Sync completed successfully. "
            summary_msg += f"Fetched: {len(raw_data)}, "
            summary_msg += f"Processed: {len(processed_records)}, "
            summary_msg += f"Saved: {len(filtered_records)}"
            
            if processing_errors:
                summary_msg += f", Errors: {len(processing_errors)}"
            
            self.logger.info(summary_msg)
            return True, summary_msg
            
        except Exception as e:
            error_msg = f"Unexpected error in sync_attendance_data: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg

    def _transform_data(self, records):
        """
        Transform raw API data into the format expected by the sync service.
        
        Args:
            records (list): List of records with format:
            [
                {
                    "pin": "8047",
                    "status": "I",
                    "created_at": "2025-09-17T07:32:39.000000Z"
                }
            ]
        """
        transformed_records = []
        for record in records:
            try:
                # Parse created_at timestamp
                created_at = record.get('created_at', '')
                if created_at.endswith('Z'):
                    # Remove Z and microseconds for parsing
                    timestamp_str = created_at.replace('Z', '').split('.')[0]
                    parsed_datetime = datetime.strptime(timestamp_str, '%Y-%m-%dT%H:%M:%S')
                else:
                    parsed_datetime = datetime.strptime(created_at, '%Y-%m-%dT%H:%M:%S')
                
                transformed_record = {
                    'pin': record.get('pin'),
                    'datetime': parsed_datetime,
                    'status': record.get('status'), # 'I' or 'O'
                    'punch': record.get('status'), # Use status as punch
                    'machine': self._get_machine_from_status(record.get('status'))
                }
                transformed_records.append(transformed_record)
            except (ValueError, TypeError) as e:
                logger.warning(f"Could not process record: {record}. Error: {e}")
        return transformed_records

    def _get_machine_from_status(self, status):
        """
        Determine the machine number based on the attendance status.
        'I' -> '114'
        'O' -> '112'
        """
        rules = {
            'I': '114',
            'O': '112'
        }
        return rules.get(status, '112') # Default to '112'


# Helper function untuk digunakan oleh scheduler
def run_online_attendance_sync():
    """
    Helper function untuk menjalankan sync yang dapat dipanggil oleh scheduler
    
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        service = OnlineAttendanceService()
        return service.sync_attendance_data()
    except Exception as e:
        error_msg = f"Error initializing OnlineAttendanceService: {str(e)}"
        logging.error(error_msg)
        return False, error_msg
