"""
spJamkerja Scheduler Service
Automatically executes spJamkerja stored procedure at scheduled intervals
Author: AI Assistant
Date: 2025-10-28
"""

import threading
import time
import logging
from datetime import datetime, timedelta
from app.models.attendance import AttendanceModel

logger = logging.getLogger(__name__)

class SpJamkerjaScheduler:
    """
    Background scheduler untuk eksekusi spJamkerja secara periodik
    - Jalan otomatis di background thread
    - Interval configurable (default: 3 jam = 10800 detik)
    - Overlap prevention (tidak double-run)
    - Parameter otomatis: kemarin s/d hari ini
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton pattern - hanya 1 instance scheduler"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize scheduler"""
        if hasattr(self, '_initialized'):
            return
        
        self._initialized = True
        self.running = False
        self.scheduler_thread = None
        self.is_processing = False
        self.last_execution_time = None
        self.last_execution_duration = None
        self.last_execution_status = None
        self.execution_count = 0
        self.success_count = 0
        self.failure_count = 0
        
        # Configuration
        self.interval_seconds = 10800  # 3 jam = 10800 detik (configurable)
        self.timeout_seconds = 5400    # 90 menit = 5400 detik
        self.auto_calculate_dates = True  # Otomatis hitung kemarin s/d hari ini
        
        logger.info("[OK] SpJamkerjaScheduler initialized")
    
    def start(self):
        """Start the scheduler"""
        if self.running:
            return False, "Scheduler is already running"
        
        self.running = True
        self.scheduler_thread = threading.Thread(
            target=self._scheduler_loop,
            daemon=True,
            name="SpJamkerjaSchedulerThread"
        )
        self.scheduler_thread.start()
        
        logger.info(f"[OK] SpJamkerja Scheduler started (interval: {self.interval_seconds}s = {self.interval_seconds/3600:.1f} hours)")
        return True, f"Scheduler started (runs every {self.interval_seconds/3600:.1f} hours)"
    
    def stop(self):
        """Stop the scheduler"""
        if not self.running:
            return False, "Scheduler is not running"
        
        self.running = False
        
        # Wait for thread to finish (max 5 seconds)
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=5)
        
        logger.info("[OK] SpJamkerja Scheduler stopped")
        return True, "Scheduler stopped"
    
    def force_execute(self):
        """
        Force immediate execution (manual trigger)
        Returns: (success, message, duration)
        """
        if self.is_processing:
            return False, "spJamkerja is already running, please wait...", None
        
        logger.info("[MANUAL] Manual execution triggered")
        return self._execute_spjamkerja()
    
    def set_interval(self, hours):
        """
        Set execution interval
        Args:
            hours: Interval dalam jam (contoh: 3, 6, 12, 24)
        """
        if hours < 0.5:  # Minimum 30 menit
            return False, "Interval minimum is 0.5 hours (30 minutes)"
        
        old_interval = self.interval_seconds / 3600
        self.interval_seconds = int(hours * 3600)
        
        logger.info(f"[CONFIG] Interval changed: {old_interval:.1f}h -> {hours:.1f}h")
        return True, f"Interval updated to {hours} hours"
    
    def get_status(self):
        """Get scheduler status"""
        return {
            'running': self.running,
            'is_processing': self.is_processing,
            'interval_hours': self.interval_seconds / 3600,
            'last_execution_time': self.last_execution_time.isoformat() if self.last_execution_time else None,
            'last_execution_duration': self.last_execution_duration,
            'last_execution_status': self.last_execution_status,
            'execution_count': self.execution_count,
            'success_count': self.success_count,
            'failure_count': self.failure_count,
            'next_execution_in_seconds': self._calculate_next_execution() if self.running else None
        }
    
    def _scheduler_loop(self):
        """Main scheduler loop (runs in background thread)"""
        logger.info("[LOOP] Scheduler loop started")
        
        # Eksekusi pertama kali setelah 5 menit startup (biar aplikasi settle dulu)
        initial_delay = 300  # 5 menit
        logger.info(f"[WAIT] First execution will run after {initial_delay} seconds...")
        time.sleep(initial_delay)
        
        while self.running:
            try:
                # Execute spJamkerja
                self._execute_spjamkerja()
                
                # Wait for next interval
                logger.info(f"[WAIT] Next execution in {self.interval_seconds} seconds ({self.interval_seconds/3600:.1f} hours)...")
                
                # Sleep in chunks untuk bisa responsive terhadap stop()
                sleep_chunk = 10  # Check setiap 10 detik
                total_slept = 0
                while total_slept < self.interval_seconds and self.running:
                    time.sleep(min(sleep_chunk, self.interval_seconds - total_slept))
                    total_slept += sleep_chunk
                
            except Exception as e:
                logger.error(f"[ERROR] Error in scheduler loop: {e}", exc_info=True)
                time.sleep(60)  # Wait 1 minute before retry
        
        logger.info("[STOP] Scheduler loop stopped")
    
    def _execute_spjamkerja(self):
        """
        Execute spJamkerja stored procedure
        Returns: (success, message, duration)
        """
        if self.is_processing:
            logger.warning("[SKIP] spJamkerja is already running, skipping this execution")
            return False, "Already running", None
        
        self.is_processing = True
        self.execution_count += 1
        execution_start = datetime.now()
        
        try:
            # Calculate date parameters (kemarin s/d hari ini)
            today = datetime.now().date()
            yesterday = today - timedelta(days=1)
            
            start_date = yesterday.strftime('%Y-%m-%d')
            end_date = today.strftime('%Y-%m-%d')
            
            logger.info(f"[EXEC] Executing spJamkerja (execution #{self.execution_count})")
            logger.info(f"[DATE] Date range: {start_date} to {end_date}")
            
            # Execute stored procedure
            attendance_model = AttendanceModel()
            success, message = attendance_model.execute_spjamkerja(start_date, end_date)
            
            # Calculate duration
            execution_end = datetime.now()
            duration_seconds = (execution_end - execution_start).total_seconds()
            
            # Update statistics
            self.last_execution_time = execution_start
            self.last_execution_duration = duration_seconds
            
            if success:
                self.success_count += 1
                self.last_execution_status = 'success'
                logger.info(f"[OK] spJamkerja completed successfully in {duration_seconds:.1f} seconds ({duration_seconds/60:.1f} minutes)")
            else:
                self.failure_count += 1
                self.last_execution_status = 'failed'
                logger.error(f"[FAIL] spJamkerja failed after {duration_seconds:.1f} seconds: {message}")
            
            return success, message, duration_seconds
            
        except Exception as e:
            execution_end = datetime.now()
            duration_seconds = (execution_end - execution_start).total_seconds()
            
            self.failure_count += 1
            self.last_execution_time = execution_start
            self.last_execution_duration = duration_seconds
            self.last_execution_status = 'error'
            
            error_msg = f"Exception during spJamkerja execution: {str(e)}"
            logger.error(f"[ERROR] {error_msg}", exc_info=True)
            
            return False, error_msg, duration_seconds
            
        finally:
            self.is_processing = False
    
    def _calculate_next_execution(self):
        """Calculate seconds until next execution"""
        if not self.last_execution_time:
            return self.interval_seconds
        
        now = datetime.now()
        next_run = self.last_execution_time + timedelta(seconds=self.interval_seconds)
        seconds_until = (next_run - now).total_seconds()
        
        return max(0, int(seconds_until))


# Singleton instance getter
_scheduler_instance = None

def get_spjamkerja_scheduler():
    """Get singleton instance of SpJamkerjaScheduler"""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = SpJamkerjaScheduler()
    return _scheduler_instance
