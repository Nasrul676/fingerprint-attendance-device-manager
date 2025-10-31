"""
Failed Attendance Upload Service
Service untuk menangani upload file Excel gagal absensi sesuai dengan flowchart
"""

import pandas as pd
import os
from datetime import datetime
from typing import Tuple, List, Dict, Any
from config.database import DatabaseManager
from config.logging_config import get_background_logger

logger = get_background_logger('FailedAttendanceUploadService', 'logs/failed_attendance_upload.log')

class FailedAttendanceUploadService:
    """Service untuk upload gagal absensi dari file Excel"""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
    
    def process_excel_upload(self, file_path: str) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Process Excel file upload sesuai flowchart
        
        Args:
            file_path: Path ke file Excel yang diupload
            
        Returns:
            Tuple[bool, str, Dict]: (success, message, statistics)
        """
        try:
            logger.info(f"Starting Excel file processing: {file_path}")
            
            # Step 1: Baca kolom tanggal, id, divisi, masuk, masuk produksi, pulang produksi, pulang dan keterangan dari file Excel
            df = self._read_excel_file(file_path)
            if df is None:
                return False, "Gagal membaca file Excel", {}
            
            logger.info(f"Excel file read successfully. Rows: {len(df)}")
            
            # Step 2: Proses data sesuai flowchart
            processed_data = []
            stats = {
                'total_rows': len(df),
                'processed_masuk': 0,
                'processed_produksi': 0,
                'processed_pulang': 0,
                'skipped_rows': 0,
                'error_rows': 0
            }
            
            for index, row in df.iterrows():
                try:
                    # Proses setiap kolom sesuai flowchart
                    row_data = self._process_row_data(row, index + 2)  # +2 karena header dan 0-indexed
                    
                    for data_item in row_data:
                        if data_item:
                            processed_data.append(data_item)
                            # Update statistics
                            if 'masuk' in data_item['keterangan'].lower():
                                stats['processed_masuk'] += 1
                            elif 'produksi' in data_item['keterangan'].lower():
                                stats['processed_produksi'] += 1
                            elif 'pulang' in data_item['keterangan'].lower():
                                stats['processed_pulang'] += 1
                
                except Exception as e:
                    logger.error(f"Error processing row {index + 2}: {e}")
                    stats['error_rows'] += 1
            
            if not processed_data:
                return False, "Tidak ada data valid untuk diproses", stats
            
            # Step 3: Insert ke database
            success, message = self._insert_to_gagalabsens(processed_data)
            
            if success:
                stats['inserted_records'] = len(processed_data)
                logger.info(f"Successfully processed {len(processed_data)} records")
                return True, f"Berhasil mengupload {len(processed_data)} record gagal absensi", stats
            else:
                return False, f"Gagal menyimpan data: {message}", stats
                
        except Exception as e:
            logger.error(f"Error in process_excel_upload: {e}")
            return False, f"Error processing file: {str(e)}", {}
        finally:
            # Cleanup temporary file
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    logger.info(f"Temporary file removed: {file_path}")
                except Exception as e:
                    logger.warning(f"Failed to remove temporary file: {e}")
    
    def _read_excel_file(self, file_path: str) -> pd.DataFrame:
        """Read Excel file dan validasi kolom yang diperlukan"""
        try:
            # Baca Excel file
            df = pd.read_excel(file_path)
            
            # Validasi kolom yang diperlukan sesuai header Excel
            required_columns = ['TANGGAL', 'ID', 'DIVISI', 'MASUK', 'MASUK PRODUKSI', 'PULANG PRODUKSI', 'PULANG', 'KETERANGAN']
            
            # Check if all required columns exist (case insensitive)
            df_columns_lower = [col.lower().strip() for col in df.columns]
            missing_columns = []
            
            for req_col in required_columns:
                if req_col.lower() not in df_columns_lower:
                    missing_columns.append(req_col)
            
            if missing_columns:
                logger.error(f"Missing required columns: {missing_columns}")
                return None
            
            # Rename columns to standard format
            column_mapping = {}
            for req_col in required_columns:
                for actual_col in df.columns:
                    if actual_col.lower().strip() == req_col.lower():
                        column_mapping[actual_col] = req_col
                        break
            
            df = df.rename(columns=column_mapping)
            
            # Remove rows with all NaN values
            df = df.dropna(how='all')
            
            logger.info(f"Excel file processed. Columns: {list(df.columns)}")
            return df
            
        except Exception as e:
            logger.error(f"Error reading Excel file: {e}")
            return None
    
    def _process_row_data(self, row: pd.Series, row_number: int) -> List[Dict[str, Any]]:
        """
        Process satu row data sesuai dengan flowchart logic
        Mengecek setiap kolom (masuk, masuk produksi, pulang produksi, pulang) dan buat record terpisah
        """
        processed_items = []
        
        try:
            # Base data dari row
            tanggal = self._parse_date(row.get('TANGGAL'))
            if not tanggal:
                logger.warning(f"Row {row_number}: Invalid or missing date")
                return []
            
            # Fix PIN - convert to integer first to remove .0, then back to string
            pin_raw = row.get('ID', '')
            try:
                # Convert to float first (in case it comes as string), then to int to remove decimals
                pin = str(int(float(str(pin_raw).strip())))
            except (ValueError, TypeError):
                logger.warning(f"Row {row_number}: Invalid PIN format: {pin_raw}")
                return []
            
            if not pin:
                logger.warning(f"Row {row_number}: Missing ID/PIN")
                return []
            
            divisi = str(row.get('DIVISI', '')).strip()
            keterangan_base = str(row.get('KETERANGAN', '')).strip()
            
            # Proses setiap kolom sesuai flowchart
            
            # 1. Cek data kolom masuk - machine: 104, status: I
            if pd.notna(row.get('MASUK')) and str(row.get('MASUK')).strip():
                masuk_time = self._parse_time(row.get('MASUK'))
                if masuk_time:
                    processed_items.append({
                        'pin': pin,
                        'tanggal': tanggal,
                        'jam': masuk_time,
                        'machine': '104',
                        'status_code': 'I',
                        'keterangan': f"masuk - {keterangan_base}" if keterangan_base else "masuk",
                        'divisi': divisi,
                        'status': 'masuk',
                        'datetime_combined': f"{tanggal} {masuk_time}"
                    })
            
            # 2. Cek data kolom masuk produksi - machine: 204, status: I
            if pd.notna(row.get('MASUK PRODUKSI')) and str(row.get('MASUK PRODUKSI')).strip():
                masuk_produksi_time = self._parse_time(row.get('MASUK PRODUKSI'))
                if masuk_produksi_time:
                    processed_items.append({
                        'pin': pin,
                        'tanggal': tanggal,
                        'jam': masuk_produksi_time,
                        'machine': '204',
                        'status_code': 'I',
                        'keterangan': f"masuk produksi - {keterangan_base}" if keterangan_base else "masuk produksi",
                        'divisi': divisi,
                        'status': 'masuk produksi',
                        'datetime_combined': f"{tanggal} {masuk_produksi_time}"
                    })
            
            # 3. Cek data kolom pulang produksi - machine: 202, status: O
            if pd.notna(row.get('PULANG PRODUKSI')) and str(row.get('PULANG PRODUKSI')).strip():
                pulang_produksi_time = self._parse_time(row.get('PULANG PRODUKSI'))
                if pulang_produksi_time:
                    processed_items.append({
                        'pin': pin,
                        'tanggal': tanggal,
                        'jam': pulang_produksi_time,
                        'machine': '202',
                        'status_code': 'O',
                        'keterangan': f"pulang produksi - {keterangan_base}" if keterangan_base else "pulang produksi",
                        'divisi': divisi,
                        'status': 'pulang produksi',
                        'datetime_combined': f"{tanggal} {pulang_produksi_time}"
                    })
            
            # 4. Cek data kolom pulang - machine: 102, status: O
            if pd.notna(row.get('PULANG')) and str(row.get('PULANG')).strip():
                pulang_time = self._parse_time(row.get('PULANG'))
                if pulang_time:
                    processed_items.append({
                        'pin': pin,
                        'tanggal': tanggal,
                        'jam': pulang_time,
                        'machine': '102',
                        'status_code': 'O',
                        'keterangan': f"pulang - {keterangan_base}" if keterangan_base else "pulang",
                        'divisi': divisi,
                        'status': 'pulang',
                        'datetime_combined': f"{tanggal} {pulang_time}"
                    })
            
            return processed_items
            
        except Exception as e:
            logger.error(f"Error processing row {row_number}: {e}")
            return []
    
    def _parse_date(self, date_value) -> str:
        """Parse tanggal ke format YYYY-MM-DD"""
        if pd.isna(date_value):
            return None
        
        try:
            if isinstance(date_value, str):
                # Try common date formats
                for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%m/%d/%Y']:
                    try:
                        dt = datetime.strptime(date_value.strip(), fmt)
                        return dt.strftime('%Y-%m-%d')
                    except:
                        continue
            elif isinstance(date_value, datetime):
                return date_value.strftime('%Y-%m-%d')
            elif hasattr(date_value, 'date'):
                return date_value.date().strftime('%Y-%m-%d')
            
            # Try pandas to_datetime as last resort
            dt = pd.to_datetime(date_value)
            return dt.strftime('%Y-%m-%d')
            
        except Exception as e:
            logger.warning(f"Failed to parse date '{date_value}': {e}")
            return None
    
    def _parse_time(self, time_value) -> str:
        """Parse waktu ke format HH:MM:SS"""
        if pd.isna(time_value):
            return None
        
        try:
            time_str = str(time_value).strip()
            
            # Handle different time formats
            if ':' in time_str:
                parts = time_str.split(':')
                if len(parts) >= 2:
                    hour = int(parts[0])
                    minute = int(parts[1])
                    second = int(parts[2]) if len(parts) > 2 else 0
                    return f"{hour:02d}:{minute:02d}:{second:02d}"
            else:
                # Handle numeric time (e.g., 800 = 08:00)
                if time_str.isdigit() and len(time_str) <= 4:
                    time_str = time_str.zfill(4)
                    hour = int(time_str[:2])
                    minute = int(time_str[2:])
                    return f"{hour:02d}:{minute:02d}:00"
            
            # Try parsing as datetime
            if isinstance(time_value, datetime):
                return time_value.strftime('%H:%M:%S')
            
            # Try pandas to_datetime
            dt = pd.to_datetime(time_str, format='%H:%M:%S')
            return dt.strftime('%H:%M:%S')
            
        except Exception as e:
            logger.warning(f"Failed to parse time '{time_value}': {e}")
            return None
    
    def _insert_to_gagalabsens(self, data_list: List[Dict[str, Any]]) -> Tuple[bool, str]:
        """
        Insert semua data ke database gagalabsens sesuai flowchart
        Format: insert into gagalabsens values('id','YYYY-MM-DD HH:MM:SS'/'masuk/status',getdate(),getdate())
        """
        if not data_list:
            return True, "No data to insert"
            
        query = """
            INSERT INTO gagalabsens (pin, tgl, machine, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, GETDATE(), GETDATE())
        """
        
        conn = self.db_manager.get_connection()
        if not conn:
            logger.error("Failed to get database connection")
            return False, "Database connection failed"
            
        try:
            cursor = conn.cursor()
            
            # Prepare batch insert data
            batch_data = []
            for item in data_list:
                # Format sesuai aturan: pin, tgl, machine, status
                batch_data.append((
                    item['pin'],  # PIN tanpa .0
                    item['datetime_combined'],  # YYYY-MM-DD HH:MM:SS format untuk kolom tgl
                    item['machine'],  # machine code sesuai aturan (104/204/202/102)
                    item['status_code']  # status code sesuai aturan (I/O)
                ))
            
            # Execute batch insert
            cursor.executemany(query, batch_data)
            conn.commit()
            
            logger.info(f"Successfully inserted {len(batch_data)} records to gagalabsens")
            return True, f"Successfully inserted {len(batch_data)} records"
            
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Error inserting to gagalabsens: {e}")
            return False, str(e)
        finally:
            if conn:
                conn.close()
    
    def validate_excel_template(self, file_path: str) -> Tuple[bool, str, List[str]]:
        """Validate Excel file structure"""
        try:
            df = pd.read_excel(file_path)
            
            required_columns = ['TANGGAL', 'ID', 'DIVISI', 'MASUK', 'MASUK PRODUKSI', 'PULANG PRODUKSI', 'PULANG', 'KETERANGAN']
            
            df_columns_lower = [col.lower().strip() for col in df.columns]
            missing_columns = []
            
            for req_col in required_columns:
                if req_col.lower() not in df_columns_lower:
                    missing_columns.append(req_col)
            
            if missing_columns:
                return False, f"Missing required columns: {', '.join(missing_columns)}", missing_columns
            
            return True, "File structure is valid", []
            
        except Exception as e:
            return False, f"Error validating file: {str(e)}", []

# Global service instance
failed_attendance_upload_service = FailedAttendanceUploadService()