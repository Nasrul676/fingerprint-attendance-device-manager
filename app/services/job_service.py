"""
Job Service untuk menangani background job processing
"""

import json
import uuid
import threading
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any, Optional, List, Callable
from config.database import db_manager
from config.logging_config import get_background_logger

# Setup logging
logger = get_background_logger('JobService', 'logs/job_service.log')

class JobStatus(Enum):
    """Job status enumeration"""
    PENDING = "pending"
    RUNNING = "running" 
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class JobType(Enum):
    """Job type enumeration"""
    PROCEDURE_PROCESSING = "procedure_processing"
    DATA_SYNC = "data_sync"
    REPORT_GENERATION = "report_generation"
    CLEANUP = "cleanup"

class Job:
    """Job data class"""
    def __init__(self, job_id: str, job_type: str, job_data: Dict[str, Any], 
                 user_id: Optional[str] = None, priority: int = 5):
        self.job_id = job_id
        self.job_type = job_type
        self.job_data = job_data
        self.user_id = user_id
        self.priority = priority
        self.status = JobStatus.PENDING
        self.attempts = 0
        self.max_attempts = 3
        self.created_at = datetime.now()
        self.started_at = None
        self.completed_at = None
        self.error_message = None
        self.result_data = None

class JobService:
    """Service untuk mengelola job queue dan processing"""
    
    def __init__(self):
        self.db_manager = db_manager
        self.is_running = False
        self.worker_thread = None
        self.job_handlers: Dict[str, Callable] = {}
        self.notification_callbacks: List[Callable] = []
        
        # Register default job handlers
        self._register_default_handlers()
        
    def _register_default_handlers(self):
        """Register default job handlers"""
        self.register_job_handler(JobType.PROCEDURE_PROCESSING.value, self._handle_procedure_processing)
        self.register_job_handler(JobType.DATA_SYNC.value, self._handle_data_sync)
        self.register_job_handler(JobType.CLEANUP.value, self._handle_cleanup)
        
    def register_job_handler(self, job_type: str, handler: Callable):
        """Register job handler untuk job type tertentu"""
        self.job_handlers[job_type] = handler
        logger.info(f"Registered job handler for type: {job_type}")
    
    def add_notification_callback(self, callback: Callable):
        """Add callback untuk notifikasi job completion"""
        self.notification_callbacks.append(callback)
    
    def create_job(self, job_type: str, job_data: Dict[str, Any], 
                   user_id: Optional[str] = None, priority: int = 5) -> str:
        """Create new job dan masukkan ke queue"""
        try:
            job_id = str(uuid.uuid4())
            
            conn = self.db_manager.get_sqlserver_connection()
            if not conn:
                raise Exception("Cannot get database connection")
            
            cursor = conn.cursor()
            
            # Insert job ke database
            insert_query = """
                INSERT INTO job_queue (job_id, job_type, job_data, status, priority, user_id)
                VALUES (?, ?, ?, ?, ?, ?)
            """
            
            cursor.execute(insert_query, (
                job_id, job_type, json.dumps(job_data), 
                JobStatus.PENDING.value, priority, user_id
            ))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"Created job {job_id} of type {job_type}")
            return job_id
            
        except Exception as e:
            logger.error(f"Error creating job: {e}")
            raise
    
    def get_job(self, job_id: str) -> Optional[Job]:
        """Get job by ID"""
        try:
            conn = self.db_manager.get_sqlserver_connection()
            if not conn:
                return None
            
            cursor = conn.cursor()
            
            query = """
                SELECT job_id, job_type, job_data, status, priority, attempts, 
                       max_attempts, created_at, started_at, completed_at, 
                       error_message, result_data, user_id
                FROM job_queue 
                WHERE job_id = ?
            """
            
            cursor.execute(query, (job_id,))
            row = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            if row:
                job = Job(row[0], row[1], json.loads(row[2] or '{}'), row[12], row[4])
                job.status = JobStatus(row[3])
                job.attempts = row[5]
                job.max_attempts = row[6]
                job.created_at = row[7]
                job.started_at = row[8]
                job.completed_at = row[9]
                job.error_message = row[10]
                job.result_data = json.loads(row[11] or '{}') if row[11] else None
                return job
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting job {job_id}: {e}")
            return None
    
    def get_jobs_by_user(self, user_id: str, limit: int = 50) -> List[Job]:
        """Get jobs untuk user tertentu"""
        try:
            conn = self.db_manager.get_sqlserver_connection()
            if not conn:
                return []
            
            cursor = conn.cursor()
            
            query = """
                SELECT TOP (?) job_id, job_type, job_data, status, priority, attempts, 
                       max_attempts, created_at, started_at, completed_at, 
                       error_message, result_data, user_id
                FROM job_queue 
                WHERE user_id = ?
                ORDER BY created_at DESC
            """
            
            cursor.execute(query, (limit, user_id))
            rows = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            jobs = []
            for row in rows:
                job = Job(row[0], row[1], json.loads(row[2] or '{}'), row[12], row[4])
                job.status = JobStatus(row[3])
                job.attempts = row[5]
                job.max_attempts = row[6]
                job.created_at = row[7]
                job.started_at = row[8]
                job.completed_at = row[9]
                job.error_message = row[10]
                job.result_data = json.loads(row[11] or '{}') if row[11] else None
                jobs.append(job)
            
            return jobs
            
        except Exception as e:
            logger.error(f"Error getting jobs for user {user_id}: {e}")
            return []
    
    def update_job_status(self, job_id: str, status: JobStatus, 
                         error_message: Optional[str] = None,
                         result_data: Optional[Dict[str, Any]] = None):
        """Update job status"""
        try:
            conn = self.db_manager.get_sqlserver_connection()
            if not conn:
                raise Exception("Cannot get database connection")
            
            cursor = conn.cursor()
            
            # Update fields berdasarkan status
            if status == JobStatus.RUNNING:
                update_query = """
                    UPDATE job_queue 
                    SET status = ?, started_at = GETDATE(), attempts = attempts + 1
                    WHERE job_id = ?
                """
                cursor.execute(update_query, (status.value, job_id))
                
            elif status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                update_query = """
                    UPDATE job_queue 
                    SET status = ?, completed_at = GETDATE(), error_message = ?, result_data = ?
                    WHERE job_id = ?
                """
                cursor.execute(update_query, (
                    status.value, error_message, 
                    json.dumps(result_data) if result_data else None, job_id
                ))
            else:
                update_query = "UPDATE job_queue SET status = ? WHERE job_id = ?"
                cursor.execute(update_query, (status.value, job_id))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"Updated job {job_id} status to {status.value}")
            
            # Send notification untuk completed/failed jobs
            if status in [JobStatus.COMPLETED, JobStatus.FAILED]:
                self._send_job_notification(job_id, status, error_message, result_data)
                
        except Exception as e:
            logger.error(f"Error updating job {job_id} status: {e}")
            raise
    
    def _send_job_notification(self, job_id: str, status: JobStatus, 
                              error_message: Optional[str] = None,
                              result_data: Optional[Dict[str, Any]] = None):
        """Send notification untuk job completion"""
        try:
            job = self.get_job(job_id)
            if not job:
                return
            
            # Create notification
            notification_id = str(uuid.uuid4())
            
            if status == JobStatus.COMPLETED:
                title = f"Job {job.job_type} Completed"
                message = f"Job {job_id} telah selesai diproses dengan sukses"
                notification_type = "job_completed"
            elif status == JobStatus.FAILED:
                title = f"Job {job.job_type} Failed"
                message = f"Job {job_id} gagal diproses: {error_message or 'Unknown error'}"
                notification_type = "job_failed"
            else:
                return
            
            # Save notification ke database
            conn = self.db_manager.get_sqlserver_connection()
            if conn:
                cursor = conn.cursor()
                
                insert_query = """
                    INSERT INTO job_notifications 
                    (notification_id, job_id, user_id, title, message, notification_type)
                    VALUES (?, ?, ?, ?, ?, ?)
                """
                
                cursor.execute(insert_query, (
                    notification_id, job_id, job.user_id, title, message, notification_type
                ))
                
                conn.commit()
                cursor.close()
                conn.close()
            
            # Call notification callbacks untuk real-time notification
            notification_data = {
                'notification_id': notification_id,
                'job_id': job_id,
                'user_id': job.user_id,
                'title': title,
                'message': message,
                'type': notification_type,
                'status': status.value,
                'timestamp': datetime.now().isoformat()
            }
            
            for callback in self.notification_callbacks:
                try:
                    callback(notification_data)
                except Exception as e:
                    logger.error(f"Error calling notification callback: {e}")
                    
        except Exception as e:
            logger.error(f"Error sending job notification: {e}")
    
    def start_worker(self):
        """Start background job worker"""
        if self.is_running:
            logger.warning("Job worker already running")
            return
        
        self.is_running = True
        self.worker_thread = threading.Thread(
            target=self._worker_loop,
            name="JobWorker",
            daemon=True
        )
        self.worker_thread.start()
        logger.info("Job worker started")
    
    def stop_worker(self):
        """Stop background job worker"""
        self.is_running = False
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=30)
        logger.info("Job worker stopped")
    
    def _worker_loop(self):
        """Main worker loop untuk processing jobs"""
        while self.is_running:
            try:
                # Get next job dari queue
                job = self._get_next_job()
                
                if job:
                    self._process_job(job)
                else:
                    # No jobs available, sleep
                    time.sleep(10)
                    
            except Exception as e:
                logger.error(f"Error in worker loop: {e}")
                time.sleep(30)  # Sleep longer on error
    
    def _get_next_job(self) -> Optional[Job]:
        """Get next job dari queue berdasarkan priority"""
        try:
            conn = self.db_manager.get_sqlserver_connection()
            if not conn:
                return None
            
            cursor = conn.cursor()
            
            # Get job dengan priority tertinggi (angka terkecil)
            query = """
                SELECT TOP 1 job_id, job_type, job_data, status, priority, attempts, 
                       max_attempts, created_at, started_at, completed_at, 
                       error_message, result_data, user_id
                FROM job_queue 
                WHERE status = ? AND attempts < max_attempts
                ORDER BY priority ASC, created_at ASC
            """
            
            cursor.execute(query, (JobStatus.PENDING.value,))
            row = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            if row:
                job = Job(row[0], row[1], json.loads(row[2] or '{}'), row[12], row[4])
                job.status = JobStatus(row[3])
                job.attempts = row[5]
                job.max_attempts = row[6]
                job.created_at = row[7]
                job.started_at = row[8]
                job.completed_at = row[9]
                job.error_message = row[10]
                job.result_data = json.loads(row[11] or '{}') if row[11] else None
                return job
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting next job: {e}")
            return None
    
    def _process_job(self, job: Job):
        """Process individual job"""
        try:
            logger.info(f"Processing job {job.job_id} of type {job.job_type}")
            
            # Update status ke running
            self.update_job_status(job.job_id, JobStatus.RUNNING)
            
            # Get job handler
            handler = self.job_handlers.get(job.job_type)
            if not handler:
                raise Exception(f"No handler found for job type: {job.job_type}")
            
            # Execute job handler
            result = handler(job)
            
            # Update status ke completed
            self.update_job_status(job.job_id, JobStatus.COMPLETED, result_data=result)
            
            logger.info(f"Completed job {job.job_id}")
            
        except Exception as e:
            error_message = str(e)
            logger.error(f"Error processing job {job.job_id}: {error_message}")
            
            # Update status ke failed
            self.update_job_status(job.job_id, JobStatus.FAILED, error_message=error_message)
            
    def _handle_procedure_processing(self, job: Job) -> Dict[str, Any]:
        """Handler untuk procedure processing jobs"""
        try:
            job_data = job.job_data
            target_date = job_data.get('target_date')
            procedures = job_data.get('procedures', ['attrecord', 'spjamkerja'])
            
            if not target_date:
                raise Exception("target_date is required for procedure processing")
            
            logger.info(f"Processing procedures {procedures} for date {target_date}")
            
            # Import attendance model
            from app.models.attendance import AttendanceModel
            attendance_model = AttendanceModel()
            
            results = {}
            
            # Process each procedure
            for procedure in procedures:
                try:
                    if procedure == 'attrecord':
                        success = attendance_model.run_attrecord_procedure(target_date)
                        results[procedure] = {
                            'success': success,
                            'message': 'attrecord procedure completed' if success else 'attrecord procedure failed'
                        }
                    elif procedure == 'spjamkerja':
                        success = attendance_model.run_spjamkerja_procedure(target_date)
                        results[procedure] = {
                            'success': success,
                            'message': 'spjamkerja procedure completed' if success else 'spjamkerja procedure failed'
                        }
                    else:
                        results[procedure] = {
                            'success': False,
                            'message': f'Unknown procedure: {procedure}'
                        }
                        
                except Exception as e:
                    results[procedure] = {
                        'success': False,
                        'message': f'Error executing {procedure}: {str(e)}'
                    }
                    logger.error(f"Error executing procedure {procedure}: {e}")
            
            # Check overall success
            overall_success = all(r.get('success', False) for r in results.values())
            
            return {
                'success': overall_success,
                'target_date': target_date,
                'procedures': results,
                'processed_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in procedure processing: {e}")
            raise
    
    def _handle_data_sync(self, job: Job) -> Dict[str, Any]:
        """Handler untuk data sync jobs"""
        # Placeholder untuk data sync jobs
        return {'success': True, 'message': 'Data sync completed'}
    
    def _handle_cleanup(self, job: Job) -> Dict[str, Any]:
        """Handler untuk cleanup jobs"""
        # Placeholder untuk cleanup jobs
        return {'success': True, 'message': 'Cleanup completed'}
    
    def get_job_statistics(self) -> Dict[str, Any]:
        """Get job queue statistics"""
        try:
            conn = self.db_manager.get_sqlserver_connection()
            if not conn:
                return {}
            
            cursor = conn.cursor()
            
            # Get status counts
            status_query = """
                SELECT status, COUNT(*) as count
                FROM job_queue
                GROUP BY status
            """
            
            cursor.execute(status_query)
            status_counts = dict(cursor.fetchall())
            
            # Get recent jobs count
            recent_query = """
                SELECT COUNT(*) as count
                FROM job_queue
                WHERE created_at >= DATEADD(hour, -24, GETDATE())
            """
            
            cursor.execute(recent_query)
            recent_count = cursor.fetchone()[0]
            
            cursor.close()
            conn.close()
            
            return {
                'status_counts': status_counts,
                'recent_jobs_24h': recent_count,
                'is_worker_running': self.is_running,
                'registered_handlers': list(self.job_handlers.keys())
            }
            
        except Exception as e:
            logger.error(f"Error getting job statistics: {e}")
            return {}

# Global job service instance
job_service = JobService()