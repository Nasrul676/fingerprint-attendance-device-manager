"""
Worker untuk menjalankan prosedur attrecord dan spjamkerja
berdasarkan data di tabel attendance_queue dengan status 'diproses'
"""

import schedule
import time
import threading
from datetime import datetime, timedelta
from collections import defaultdict
from app.models.attendance import AttendanceModel
from config.logging_config import get_worker_logger

# Setup logging with Unicode support
logger = get_worker_logger()

class AttendanceWorker:
    """Worker untuk memproses antrian absensi dan menjalankan prosedur SQL"""
    
    def __init__(self):
        self.attendance_model = AttendanceModel()
        self.is_running = False
        self._stop_event = threading.Event()
        self.activity_callback = None  # Callback function untuk activity log
    
    def set_activity_callback(self, callback):
        """Set callback function untuk activity log"""
        self.activity_callback = callback
    
    def _log_activity(self, message, level='INFO'):
        """Log activity ke callback jika tersedia"""
        if self.activity_callback:
            try:
                self.activity_callback(message, level)
            except Exception as e:
                logger.error(f"Error in activity callback: {str(e)}")
        
    def process_attendance_queue(self):
        """Memproses antrian absensi dengan status 'baru'"""
        try:
            logger.info("[WORKER] Memulai pemrosesan antrian absensi...")
            
            # Ambil data dari antrian dengan status 'baru'
            queue_records = self.attendance_model.get_attendance_queue(status='baru')
            
            if not queue_records:
                logger.info("[WORKER] Tidak ada data dengan status 'baru' dalam antrian")
                return
            
            logger.info(f"[WORKER] Ditemukan {len(queue_records)} record dengan status 'baru'")
            
            # Kelompokkan berdasarkan tanggal
            date_groups = self._group_by_date(queue_records)

            target_date = datetime.now() - timedelta(days=2)
            target_date_str = target_date.strftime('%Y-%m-%d')
            
            # Proses hanya untuk tanggal target
            if target_date_str in date_groups:
                records = date_groups[target_date_str]
                logger.info(f"[WORKER] Memproses tanggal target: {target_date_str} ({len(records)} records)")

                # Update status menjadi 'diproses' sebelum menjalankan prosedur
                self._update_records_status(records, 'diproses')

                # Jalankan prosedur untuk tanggal ini
                success = self._run_procedures_for_date(target_date_str)

                if success:
                    # Update status record menjadi 'selesai'
                    self._update_records_status(records, 'selesai')
                    logger.info(f"[SUCCESS] Berhasil memproses tanggal {target_date_str}")
                else:
                    # Jika gagal, kembalikan status ke 'baru'
                    self._update_records_status(records, 'baru')
                    logger.error(f"[ERROR] Gagal memproses tanggal {target_date_str}, status dikembalikan ke 'baru'")
            else:
                logger.info(f"[WORKER] Tidak ada data untuk tanggal target {target_date_str} yang perlu diproses.")
            
            logger.info("[DONE] Selesai memproses antrian absensi")
            
        except Exception as e:
            logger.error(f"[ERROR] Error dalam pemrosesan antrian: {str(e)}")
    
    def _group_by_date(self, records):
        """Kelompokkan record berdasarkan tanggal"""
        date_groups = defaultdict(list)
        
        for record in records:
            # Ambil tanggal saja (tanpa waktu) - use uppercase Date key from model
            record_date = record.get('Date') or record.get('date')
            if record_date:
                date_str = record_date.strftime('%Y-%m-%d')
                date_groups[date_str].append(record)
        
        return date_groups
    
    def _run_procedures_for_date(self, date_str):
        """Jalankan prosedur attrecord dan spjamkerja untuk tanggal tertentu"""
        try:
            logger.info(f"[PROCESS] Menjalankan prosedur untuk tanggal {date_str}")
            
            # Jalankan prosedur attrecord
            logger.info(f"[ATTRECORD] Menjalankan prosedur attrecord...")
            success_att, message_att = self.attendance_model.execute_attrecord_procedure(date_str, date_str)
            
            if not success_att:
                logger.error(f"[ERROR] Gagal menjalankan attrecord: {message_att}")
                return False
            
            logger.info(f"[SUCCESS] attrecord berhasil: {message_att}")
            
            # Jalankan prosedur spjamkerja
            logger.info(f"[SPJAMKERJA] Menjalankan prosedur spjamkerja...")
            success_jam, message_jam = self.attendance_model.execute_spjamkerja_procedure(date_str, date_str)
            
            if not success_jam:
                logger.error(f"[ERROR] Gagal menjalankan spjamkerja: {message_jam}")
                return False
            
            logger.info(f"[SUCCESS] spjamkerja berhasil: {message_jam}")
            
            return True
            
        except Exception as e:
            logger.error(f"[ERROR] Error menjalankan prosedur untuk {date_str}: {str(e)}")
            return False
    
    def _update_records_status(self, records, new_status):
        """Update status untuk semua record dalam kelompok"""
        try:
            for record in records:
                # Use uppercase ID key from model
                record_id = record.get('ID') or record.get('id')
                success, message = self.attendance_model.update_queue_status(record_id, new_status)
                if not success:
                    logger.warning(f"[WARNING] Gagal update status record {record_id}: {message}")
                    
        except Exception as e:
            logger.error(f"[ERROR] Error update status: {str(e)}")
    
    def start_scheduler(self):
        """Memulai scheduler worker dengan background threading"""
        if self.is_running:
            logger.warning("[WARNING] Worker sudah berjalan")
            return
        
        self.is_running = True
        logger.info("[START] Memulai Attendance Worker...")
        
        # Schedule job untuk berjalan setiap 1 jam
        schedule.every().hour.do(self._process_attendance_queue_safe)
        
        # Jalankan sekali saat startup dalam thread terpisah
        logger.info("[INIT] Menjalankan pemrosesan pertama kali...")
        initial_thread = threading.Thread(
            target=self._process_attendance_queue_safe,
            name="InitialProcessing",
            daemon=True
        )
        initial_thread.start()
        
        # Loop scheduler dengan sleep yang lebih optimal
        while self.is_running and not self._stop_event.is_set():
            try:
                schedule.run_pending()
                # Gunakan wait dengan timeout untuk responsiveness yang lebih baik
                self._stop_event.wait(timeout=300)  # Check setiap 5 menit
                
            except KeyboardInterrupt:
                logger.info("[STOP] Menerima signal stop dari keyboard")
                break
            except Exception as e:
                logger.error(f"[ERROR] Error dalam scheduler loop: {str(e)}")
                self._stop_event.wait(timeout=60)  # Wait 1 menit sebelum retry
        
        logger.info("[STOP] Attendance Worker dihentikan")
    
    def process_attendance_queue_with_filters(self, start_date=None, end_date=None, pins_filter=None):
        """Memproses antrian absensi dengan filter tanggal dan PINs"""
        result = {
            'success': False,
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'summary': '',
            'processing_time': 0.0
        }
        
        start_time = time.time()
        
        try:
            # Build filter info untuk logging
            filter_parts = []
            if start_date and end_date:
                filter_parts.append(f"Tanggal: {start_date} - {end_date}")
            elif start_date:
                filter_parts.append(f"Tanggal: {start_date} ke atas")
            elif end_date:
                filter_parts.append(f"Tanggal: sampai {end_date}")
            
            if pins_filter:
                pins_preview = pins_filter[:3] + (['...'] if len(pins_filter) > 3 else [])
                filter_parts.append(f"PINs: {', '.join(map(str, pins_preview))} ({len(pins_filter)} total)")
            
            filter_info = f" dengan filter {'; '.join(filter_parts)}" if filter_parts else ""
            
            logger.info(f"[WORKER] Memulai pemrosesan antrian absensi{filter_info}")
            self._log_activity(f"🚀 Memulai pemrosesan antrian{filter_info}...", 'INFO')
            
            # Ambil data dari antrian dengan status 'baru'
            queue_records = self.attendance_model.get_attendance_queue(status='baru')
            original_count = len(queue_records)
            result['total_processed'] = original_count
            
            if not queue_records:
                logger.info("[WORKER] Tidak ada data dengan status 'baru' dalam antrian")
                self._log_activity("💭 Tidak ada data baru untuk diproses", 'INFO')
                result['success'] = True
                result['summary'] = "Tidak ada data untuk diproses"
                return result
            
            logger.info(f"[WORKER] Ditemukan {len(queue_records)} record dengan status 'baru'")
            self._log_activity(f"📊 Ditemukan {len(queue_records)} record dalam antrian", 'INFO')
            
            # Apply date filtering if specified
            if start_date or end_date:
                filtered_records = []
                for record in queue_records:
                    record_date = record.get('Date') or record.get('date')
                    if record_date:
                        record_date_str = record_date.strftime('%Y-%m-%d')
                        
                        # Check date range
                        if start_date and record_date_str < start_date:
                            continue
                        if end_date and record_date_str > end_date:
                            continue
                        
                        filtered_records.append(record)
                
                queue_records = filtered_records
                logger.info(f"[WORKER] Setelah filter tanggal: {len(queue_records)} record")
                self._log_activity(f"📅 Setelah filter tanggal: {len(queue_records)} record", 'INFO')
            
            # Apply PINs filtering if specified
            if pins_filter:
                filtered_records = []
                for record in queue_records:
                    record_pin = str(record.get('PIN', ''))
                    if record_pin in pins_filter:
                        filtered_records.append(record)
                
                queue_records = filtered_records
                logger.info(f"[WORKER] Setelah filter PINs: {len(queue_records)} record")
                self._log_activity(f"👥 Setelah filter PINs: {len(queue_records)} record", 'INFO')
            
            if not queue_records:
                logger.info("[WORKER] Tidak ada data yang cocok dengan filter")
                self._log_activity("💭 Tidak ada data yang cocok dengan filter", 'INFO')
                result['success'] = True
                result['summary'] = "Tidak ada data yang cocok dengan filter"
                return result
            
            # Process the filtered records
            date_groups = self._group_by_date(queue_records)
            successful_dates = 0
            failed_dates = 0
            
            for date_str, records in date_groups.items():
                try:
                    logger.info(f"[WORKER] Memproses tanggal: {date_str} ({len(records)} records)")
                    self._log_activity(f"📝 Memproses {date_str}: {len(records)} records", 'INFO')
                    
                    # Update status to 'diproses'
                    self._update_records_status(records, 'diproses')
                    
                    # Extract unique PINs for this date
                    pins = list(set([str(record.get('PIN', '')) for record in records]))
                    
                    # Execute procedures with PIN filter
                    success_attrecord, msg_attrecord = self.attendance_model.execute_attrecord_procedure(date_str, date_str, pins=pins)
                    success_spjamkerja, msg_spjamkerja = self.attendance_model.execute_spjamkerja_procedure(date_str, date_str, pins=pins)
                    
                    if success_attrecord and success_spjamkerja:
                        # Update status to 'selesai'
                        self._update_records_status(records, 'selesai')
                        successful_dates += 1
                        self._log_activity(f"✅ Berhasil: {date_str}", 'INFO')
                    else:
                        # Update status back to 'baru' for retry
                        self._update_records_status(records, 'baru')
                        failed_dates += 1
                        error_msg = f"Gagal {date_str}: {msg_attrecord or msg_spjamkerja}"
                        self._log_activity(f"❌ {error_msg}", 'ERROR')
                        
                except Exception as e:
                    failed_dates += 1
                    error_msg = f"Error processing {date_str}: {str(e)}"
                    logger.error(f"[WORKER] {error_msg}")
                    self._log_activity(f"❌ Error {date_str}: {str(e)}", 'ERROR')
            
            # Update result
            result['successful'] = successful_dates
            result['failed'] = failed_dates
            result['success'] = failed_dates == 0
            result['processing_time'] = time.time() - start_time
            result['summary'] = f"Berhasil: {successful_dates}, Gagal: {failed_dates}"
            
            # Log final result
            self._log_activity(f"✅ Selesai! Berhasil: {successful_dates}, Gagal: {failed_dates}", 'INFO')
            logger.info(f"[WORKER] Pemrosesan selesai. Berhasil: {successful_dates}, Gagal: {failed_dates}")
            
            return result
            
        except Exception as e:
            result['processing_time'] = time.time() - start_time
            result['summary'] = f"Error: {str(e)}"
            error_msg = f"❌ Error dalam pemrosesan: {str(e)}"
            self._log_activity(error_msg, 'ERROR')
            logger.error(f"[WORKER] {error_msg}")
            return result
    
    def _process_attendance_queue_safe(self):
        """Wrapper untuk process_attendance_queue dengan error handling yang aman"""
        try:
            self.process_attendance_queue()
        except Exception as e:
            logger.error(f"[ERROR] Error dalam background processing: {str(e)}")
            # Jangan crash worker, hanya log error
    
    def stop_scheduler(self):
        """Menghentikan scheduler worker"""
        logger.info("[STOP] Menghentikan Attendance Worker...")
        self.is_running = False
        self._stop_event.set()
        schedule.clear()
    
    def get_status(self):
        """Mendapatkan status worker"""
        queue_stats = self._get_queue_stats()
        
        return {
            'is_running': self.is_running,
            'next_run': schedule.next_run() if schedule.jobs else None,
            'queue_stats': queue_stats,
            'schedule_info': f"Setiap 1 jam ({len(schedule.jobs)} jobs scheduled)"
        }
    
    def _get_queue_stats(self):
        """Mendapatkan statistik antrian"""
        try:
            all_records = self.attendance_model.get_attendance_queue()
            
            stats = {
                'total': len(all_records),
                'by_status': {},
                'baru_dates': []
            }
            
            for record in all_records:
                status = record['Status']
                stats['by_status'][status] = stats['by_status'].get(status, 0) + 1
                
                # Kumpulkan tanggal untuk status 'baru' (yang akan diproses)
                if status == 'baru' and record['Date']:
                    date_str = record['Date'].strftime('%Y-%m-%d')
                    if date_str not in stats['baru_dates']:
                        stats['baru_dates'].append(date_str)
            
            stats['baru_dates'].sort()
            return stats
            
        except Exception as e:
            logger.error(f"Error getting queue stats: {str(e)}")
            return {'error': str(e)}

def run_worker():
    """Fungsi untuk menjalankan worker"""
    worker = AttendanceWorker()
    
    try:
        worker.start_scheduler()
    except KeyboardInterrupt:
        worker.stop_scheduler()
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        worker.stop_scheduler()

if __name__ == '__main__':
    run_worker()
