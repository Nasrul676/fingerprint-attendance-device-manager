"""
Service untuk mengelola Attendance Worker
"""

import threading
import time
from datetime import datetime
from app.workers.attendance_worker import AttendanceWorker

class AttendanceWorkerService:
    """Service untuk mengelola worker attendance"""
    
    def __init__(self):
        self.worker = AttendanceWorker()
        self.worker_thread = None
        
    def start_worker(self):
        """Memulai worker dalam thread terpisah"""
        if self.worker_thread and self.worker_thread.is_alive():
            return False, "Worker sudah berjalan"
        
        try:
            self.worker_thread = threading.Thread(target=self.worker.start_scheduler, daemon=True)
            self.worker_thread.start()
            
            # Tunggu sebentar untuk memastikan worker mulai
            time.sleep(1)
            
            return True, "Worker berhasil dimulai"
            
        except Exception as e:
            return False, f"Error memulai worker: {str(e)}"
    
    def stop_worker(self):
        """Menghentikan worker"""
        try:
            self.worker.stop_scheduler()
            
            # Tunggu thread selesai (maksimal 5 detik)
            if self.worker_thread:
                self.worker_thread.join(timeout=5)
            
            return True, "Worker berhasil dihentikan"
            
        except Exception as e:
            return False, f"Error menghentikan worker: {str(e)}"
    
    def get_worker_status(self):
        """Mendapatkan status worker"""
        try:
            base_status = self.worker.get_status()
            
            thread_status = {
                'thread_alive': self.worker_thread.is_alive() if self.worker_thread else False,
                'thread_name': self.worker_thread.name if self.worker_thread else None
            }
            
            return {**base_status, **thread_status}
            
        except Exception as e:
            return {'error': str(e)}
    
    def force_run_now(self):
        """Paksa menjalankan pemrosesan sekarang"""
        try:
            # Jalankan dalam thread terpisah agar tidak blocking
            process_thread = threading.Thread(
                target=self.worker.process_attendance_queue,
                daemon=True
            )
            process_thread.start()
            
            return True, "Pemrosesan manual dimulai"
            
        except Exception as e:
            return False, f"Error menjalankan pemrosesan manual: {str(e)}"

# Global instance
attendance_worker_service = AttendanceWorkerService()
