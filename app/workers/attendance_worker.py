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
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/attendance_worker.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('AttendanceWorker')

class AttendanceWorker:
    """Worker untuk memproses antrian absensi dan menjalankan prosedur SQL"""
    
    def __init__(self):
        self.attendance_model = AttendanceModel()
        self.is_running = False
        self._stop_event = threading.Event()
        
    def process_attendance_queue(self):
        """Memproses antrian absensi dengan status 'baru'"""
        try:
            logger.info("[WORKER] Memulai pemrosesan antrian absensi...")
            
            # Ambil data dari antrian dengan status 'baru'
            queue_records = self.attendance_model.get_attendance_queue(status='baru', limit=1000)
            
            if not queue_records:
                logger.info("[WORKER] Tidak ada data dengan status 'baru' dalam antrian")
                return
            
            logger.info(f"[WORKER] Ditemukan {len(queue_records)} record dengan status 'baru'")
            
            # Kelompokkan berdasarkan tanggal
            date_groups = self._group_by_date(queue_records)
            
            # Proses setiap kelompok tanggal
            for date_str, records in date_groups.items():
                logger.info(f"📅 Memproses tanggal: {date_str} ({len(records)} records)")
                
                # Update status menjadi 'diproses' sebelum menjalankan prosedur
                self._update_records_status(records, 'diproses')
                
                # Jalankan prosedur untuk tanggal ini
                success = self._run_procedures_for_date(date_str)
                
                if success:
                    # Update status record menjadi 'selesai'
                    self._update_records_status(records, 'selesai')
                    logger.info(f"[SUCCESS] Berhasil memproses tanggal {date_str}")
                else:
                    # Jika gagal, kembalikan status ke 'baru'
                    self._update_records_status(records, 'baru')
                    logger.error(f"[ERROR] Gagal memproses tanggal {date_str}, status dikembalikan ke 'baru'")
            
            logger.info("[DONE] Selesai memproses antrian absensi")
            
        except Exception as e:
            logger.error(f"[ERROR] Error dalam pemrosesan antrian: {str(e)}")
    
    def _group_by_date(self, records):
        """Kelompokkan record berdasarkan tanggal"""
        date_groups = defaultdict(list)
        
        for record in records:
            # Ambil tanggal saja (tanpa waktu)
            if record['date']:
                date_str = record['date'].strftime('%Y-%m-%d')
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
                success, message = self.attendance_model.update_queue_status(record['id'], new_status)
                if not success:
                    logger.warning(f"[WARNING] Gagal update status record {record['id']}: {message}")
                    
        except Exception as e:
            logger.error(f"[ERROR] Error update status: {str(e)}")
    
    def start_scheduler(self):
        """Memulai scheduler worker"""
        if self.is_running:
            logger.warning("[WARNING] Worker sudah berjalan")
            return
        
        self.is_running = True
        logger.info("[START] Memulai Attendance Worker...")
        
        # Schedule job setiap 30 menit
        schedule.every(30).minutes.do(self.process_attendance_queue)
        
        # Jalankan sekali saat startup
        logger.info("[INIT] Menjalankan pemrosesan pertama kali...")
        self.process_attendance_queue()
        
        # Loop scheduler
        while self.is_running and not self._stop_event.is_set():
            try:
                schedule.run_pending()
                time.sleep(60)  # Check setiap menit
                
            except KeyboardInterrupt:
                logger.info("[STOP] Menerima signal stop dari keyboard")
                break
            except Exception as e:
                logger.error(f"[ERROR] Error dalam scheduler loop: {str(e)}")
                time.sleep(60)
        
        logger.info("🛑 Attendance Worker dihentikan")
    
    def stop_scheduler(self):
        """Menghentikan scheduler worker"""
        logger.info("🛑 Menghentikan Attendance Worker...")
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
            'schedule_info': f"Setiap 30 menit ({len(schedule.jobs)} jobs scheduled)"
        }
    
    def _get_queue_stats(self):
        """Mendapatkan statistik antrian"""
        try:
            all_records = self.attendance_model.get_attendance_queue(limit=10000)
            
            stats = {
                'total': len(all_records),
                'by_status': {},
                'baru_dates': []
            }
            
            for record in all_records:
                status = record['status']
                stats['by_status'][status] = stats['by_status'].get(status, 0) + 1
                
                # Kumpulkan tanggal untuk status 'baru' (yang akan diproses)
                if status == 'baru' and record['date']:
                    date_str = record['date'].strftime('%Y-%m-%d')
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
