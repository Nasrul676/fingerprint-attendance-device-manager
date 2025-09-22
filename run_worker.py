#!/usr/bin/env python3
"""
Standalone script untuk menjalankan Attendance Worker dan Job Service
"""

import sys
import os
import threading
import time
import signal

# Add project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.workers.attendance_worker import run_worker
from app.services.job_service import job_service
from config.logging_config import get_background_logger

# Setup logging
logger = get_background_logger('WorkerMain', 'logs/worker_main.log')

class WorkerManager:
    """Manager untuk menjalankan multiple workers"""
    
    def __init__(self):
        self.is_running = False
        self.workers = []
        self.shutdown_event = threading.Event()
        
    def start(self):
        """Start semua workers"""
        self.is_running = True
        
        print("🚀 Starting Attendance System Workers...")
        logger.info("Starting worker manager")
        
        try:
            # Start job service worker
            print("📋 Starting Job Service Worker...")
            job_service.start_worker()
            print("✅ Job Service Worker started")
            
            # Start attendance worker dalam thread terpisah
            print("🔄 Starting Attendance Worker...")
            attendance_worker_thread = threading.Thread(
                target=self._run_attendance_worker,
                name="AttendanceWorkerThread",
                daemon=True
            )
            attendance_worker_thread.start()
            self.workers.append(attendance_worker_thread)
            print("✅ Attendance Worker started")
            
            print("\n🎯 All workers are running!")
            print("Workers:")
            print("  - Job Service Worker: Background job processing")
            print("  - Attendance Worker: Scheduled attendance queue processing")
            print("\nTekan Ctrl+C untuk menghentikan semua workers\n")
            
            # Main loop - keep alive
            self._keep_alive()
            
        except Exception as e:
            logger.error(f"Error starting workers: {e}")
            print(f"❌ Error starting workers: {e}")
            self.stop()
            
    def _run_attendance_worker(self):
        """Run attendance worker dengan exception handling"""
        try:
            run_worker()
        except Exception as e:
            logger.error(f"Attendance worker error: {e}")
            print(f"❌ Attendance worker error: {e}")
    
    def _keep_alive(self):
        """Keep main thread alive"""
        try:
            while self.is_running and not self.shutdown_event.is_set():
                # Log status setiap 5 menit
                if self.shutdown_event.wait(300):  # 5 minutes
                    break
                    
                logger.info("Workers status check - all running")
                
        except KeyboardInterrupt:
            print("\n🛑 Shutdown signal received...")
            self.stop()
    
    def stop(self):
        """Stop semua workers"""
        if not self.is_running:
            return
            
        print("🛑 Stopping workers...")
        logger.info("Stopping worker manager")
        
        self.is_running = False
        self.shutdown_event.set()
        
        try:
            # Stop job service
            print("📋 Stopping Job Service Worker...")
            job_service.stop_worker()
            print("✅ Job Service Worker stopped")
            
            # Wait for attendance worker threads
            print("🔄 Stopping Attendance Worker...")
            for worker in self.workers:
                if worker.is_alive():
                    worker.join(timeout=30)
            print("✅ Attendance Worker stopped")
            
            print("✅ All workers stopped successfully")
            logger.info("All workers stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping workers: {e}")
            print(f"❌ Error stopping workers: {e}")

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    print(f"\n📡 Received signal {signum}")
    if 'worker_manager' in globals():
        worker_manager.stop()
    sys.exit(0)

if __name__ == '__main__':
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create and start worker manager
    worker_manager = WorkerManager()
    
    try:
        worker_manager.start()
    except KeyboardInterrupt:
        print("\n🛑 Workers dihentikan oleh user")
    except Exception as e:
        print(f"\n❌ Worker manager error: {str(e)}")
        logger.error(f"Worker manager error: {e}")
        sys.exit(1)
    finally:
        worker_manager.stop()
