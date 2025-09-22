"""
Job Controller untuk menangani job-related endpoints
"""

import json
from flask import request, jsonify, session
from datetime import datetime, date
from app.services.job_service import job_service, JobType, JobStatus
from config.logging_config import get_background_logger

# Setup logging
logger = get_background_logger('JobController', 'logs/job_controller.log')

class JobController:
    """Controller untuk job management"""
    
    def __init__(self):
        self.job_service = job_service
    
    def create_procedure_job(self):
        """Create job untuk procedure processing"""
        try:
            data = request.get_json()
            
            if not data:
                return jsonify({
                    'success': False,
                    'message': 'No data provided'
                }), 400
            
            # Validate required fields
            target_date = data.get('target_date')
            if not target_date:
                return jsonify({
                    'success': False,
                    'message': 'target_date is required'
                }), 400
            
            # Validate date format
            try:
                datetime.strptime(target_date, '%Y-%m-%d')
            except ValueError:
                return jsonify({
                    'success': False,
                    'message': 'Invalid date format. Use YYYY-MM-DD'
                }), 400
            
            # Get procedures to run
            procedures = data.get('procedures', ['attrecord', 'spjamkerja'])
            if not isinstance(procedures, list):
                return jsonify({
                    'success': False,
                    'message': 'procedures must be a list'
                }), 400
            
            # Valid procedures
            valid_procedures = ['attrecord', 'spjamkerja']
            invalid_procedures = [p for p in procedures if p not in valid_procedures]
            if invalid_procedures:
                return jsonify({
                    'success': False,
                    'message': f'Invalid procedures: {invalid_procedures}. Valid: {valid_procedures}'
                }), 400
            
            # Get user info from session
            user_id = session.get('user_id', 'system')
            
            # Get priority (optional)
            priority = data.get('priority', 5)
            if not isinstance(priority, int) or priority < 1 or priority > 10:
                priority = 5
            
            # Create job data
            job_data = {
                'target_date': target_date,
                'procedures': procedures,
                'requested_by': user_id,
                'request_time': datetime.now().isoformat()
            }
            
            # Create job
            job_id = self.job_service.create_job(
                job_type=JobType.PROCEDURE_PROCESSING.value,
                job_data=job_data,
                user_id=user_id,
                priority=priority
            )
            
            logger.info(f"Created procedure job {job_id} for date {target_date} by user {user_id}")
            
            return jsonify({
                'success': True,
                'message': 'Job created successfully',
                'job_id': job_id,
                'target_date': target_date,
                'procedures': procedures,
                'status': 'pending'
            })
            
        except Exception as e:
            logger.error(f"Error creating procedure job: {e}")
            return jsonify({
                'success': False,
                'message': f'Error creating job: {str(e)}'
            }), 500
    
    def get_job_status(self, job_id):
        """Get status dari specific job"""
        try:
            job = self.job_service.get_job(job_id)
            
            if not job:
                return jsonify({
                    'success': False,
                    'message': 'Job not found'
                }), 404
            
            # Build response
            response = {
                'success': True,
                'job': {
                    'job_id': job.job_id,
                    'job_type': job.job_type,
                    'status': job.status.value,
                    'priority': job.priority,
                    'attempts': job.attempts,
                    'max_attempts': job.max_attempts,
                    'created_at': job.created_at.isoformat() if job.created_at else None,
                    'started_at': job.started_at.isoformat() if job.started_at else None,
                    'completed_at': job.completed_at.isoformat() if job.completed_at else None,
                    'job_data': job.job_data,
                    'user_id': job.user_id
                }
            }
            
            # Add error message if failed
            if job.status == JobStatus.FAILED and job.error_message:
                response['job']['error_message'] = job.error_message
            
            # Add result data if completed
            if job.status == JobStatus.COMPLETED and job.result_data:
                response['job']['result_data'] = job.result_data
            
            return jsonify(response)
            
        except Exception as e:
            logger.error(f"Error getting job status {job_id}: {e}")
            return jsonify({
                'success': False,
                'message': f'Error getting job status: {str(e)}'
            }), 500
    
    def get_user_jobs(self):
        """Get jobs untuk current user"""
        try:
            user_id = session.get('user_id', 'system')
            limit = request.args.get('limit', 50, type=int)
            
            # Validate limit
            if limit < 1 or limit > 200:
                limit = 50
            
            jobs = self.job_service.get_jobs_by_user(user_id, limit)
            
            # Format jobs untuk response
            jobs_data = []
            for job in jobs:
                job_data = {
                    'job_id': job.job_id,
                    'job_type': job.job_type,
                    'status': job.status.value,
                    'priority': job.priority,
                    'attempts': job.attempts,
                    'max_attempts': job.max_attempts,
                    'created_at': job.created_at.isoformat() if job.created_at else None,
                    'started_at': job.started_at.isoformat() if job.started_at else None,
                    'completed_at': job.completed_at.isoformat() if job.completed_at else None,
                    'job_data': job.job_data
                }
                
                # Add error message if failed
                if job.status == JobStatus.FAILED and job.error_message:
                    job_data['error_message'] = job.error_message
                
                # Add result summary for completed jobs
                if job.status == JobStatus.COMPLETED and job.result_data:
                    job_data['result_summary'] = self._get_result_summary(job)
                
                jobs_data.append(job_data)
            
            return jsonify({
                'success': True,
                'jobs': jobs_data,
                'total': len(jobs_data),
                'user_id': user_id
            })
            
        except Exception as e:
            logger.error(f"Error getting user jobs: {e}")
            return jsonify({
                'success': False,
                'message': f'Error getting jobs: {str(e)}'
            }), 500
    
    def get_job_statistics(self):
        """Get job queue statistics"""
        try:
            stats = self.job_service.get_job_statistics()
            
            return jsonify({
                'success': True,
                'statistics': stats
            })
            
        except Exception as e:
            logger.error(f"Error getting job statistics: {e}")
            return jsonify({
                'success': False,
                'message': f'Error getting statistics: {str(e)}'
            }), 500
    
    def cancel_job(self, job_id):
        """Cancel pending job"""
        try:
            job = self.job_service.get_job(job_id)
            
            if not job:
                return jsonify({
                    'success': False,
                    'message': 'Job not found'
                }), 404
            
            # Check if job can be cancelled
            if job.status not in [JobStatus.PENDING]:
                return jsonify({
                    'success': False,
                    'message': f'Cannot cancel job with status: {job.status.value}'
                }), 400
            
            # Check user permissions
            user_id = session.get('user_id', 'system')
            if job.user_id != user_id and user_id != 'admin':
                return jsonify({
                    'success': False,
                    'message': 'Not authorized to cancel this job'
                }), 403
            
            # Cancel job
            self.job_service.update_job_status(job_id, JobStatus.CANCELLED)
            
            logger.info(f"Cancelled job {job_id} by user {user_id}")
            
            return jsonify({
                'success': True,
                'message': 'Job cancelled successfully',
                'job_id': job_id
            })
            
        except Exception as e:
            logger.error(f"Error cancelling job {job_id}: {e}")
            return jsonify({
                'success': False,
                'message': f'Error cancelling job: {str(e)}'
            }), 500
    
    def get_job_notifications(self):
        """Get notifications untuk current user"""
        try:
            user_id = session.get('user_id', 'system')
            limit = request.args.get('limit', 20, type=int)
            unread_only = request.args.get('unread_only', False, type=bool)
            
            # Validate limit
            if limit < 1 or limit > 100:
                limit = 20
            
            # Get notifications dari database
            from config.database import db_manager
            conn = db_manager.get_sqlserver_connection()
            if not conn:
                return jsonify({
                    'success': False,
                    'message': 'Database connection failed'
                }), 500
            
            cursor = conn.cursor()
            
            # Build query
            where_clause = "WHERE user_id = ?"
            params = [user_id]
            
            if unread_only:
                where_clause += " AND is_read = 0"
            
            query = f"""
                SELECT TOP (?) notification_id, job_id, title, message, notification_type,
                       is_read, created_at
                FROM job_notifications
                {where_clause}
                ORDER BY created_at DESC
            """
            
            cursor.execute(query, [limit] + params)
            rows = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            # Format notifications
            notifications = []
            for row in rows:
                notifications.append({
                    'notification_id': row[0],
                    'job_id': row[1],
                    'title': row[2],
                    'message': row[3],
                    'type': row[4],
                    'is_read': bool(row[5]),
                    'created_at': row[6].isoformat() if row[6] else None
                })
            
            return jsonify({
                'success': True,
                'notifications': notifications,
                'total': len(notifications),
                'user_id': user_id
            })
            
        except Exception as e:
            logger.error(f"Error getting job notifications: {e}")
            return jsonify({
                'success': False,
                'message': f'Error getting notifications: {str(e)}'
            }), 500
    
    def get_job_queue(self):
        """Get job queue dengan filtering dan pagination"""
        try:
            # Get query parameters
            status = request.args.get('status')
            priority = request.args.get('priority')
            job_type = request.args.get('job_type')
            date_range = request.args.get('date_range')
            limit = request.args.get('limit', 50, type=int)
            offset = request.args.get('offset', 0, type=int)
            
            # Get user context
            user_id = session.get('user_id', 'system')
            
            # Build query
            from config.database import db_manager
            conn = db_manager.get_sqlserver_connection()
            if not conn:
                return jsonify({
                    'success': False,
                    'message': 'Database connection failed'
                }), 500
            
            cursor = conn.cursor()
            
            # Build WHERE clause
            where_conditions = ["user_id = ?"]
            params = [user_id]
            
            if status and status != 'all':
                where_conditions.append("status = ?")
                params.append(status)
            
            if priority:
                priority_values = priority.split(',')
                placeholders = ','.join(['?' for _ in priority_values])
                where_conditions.append(f"priority IN ({placeholders})")
                params.extend(priority_values)
            
            if job_type:
                where_conditions.append("job_type = ?")
                params.append(job_type)
            
            if date_range:
                if date_range == 'today':
                    where_conditions.append("CAST(created_at AS DATE) = CAST(GETDATE() AS DATE)")
                elif date_range == 'yesterday':
                    where_conditions.append("CAST(created_at AS DATE) = CAST(DATEADD(day, -1, GETDATE()) AS DATE)")
                elif date_range == 'week':
                    where_conditions.append("created_at >= DATEADD(week, -1, GETDATE())")
                elif date_range == 'month':
                    where_conditions.append("created_at >= DATEADD(month, -1, GETDATE())")
            
            where_clause = " AND ".join(where_conditions)
            
            # Get total count
            count_query = f"SELECT COUNT(*) FROM job_queue WHERE {where_clause}"
            cursor.execute(count_query, params)
            total_count = cursor.fetchone()[0]
            
            # Get jobs with pagination
            query = f"""
                SELECT job_id, job_type, job_data, status, priority, attempts, 
                       max_attempts, created_at, started_at, completed_at, 
                       error_message, result_data, user_id
                FROM job_queue 
                WHERE {where_clause}
                ORDER BY 
                    CASE WHEN status = 'running' THEN 1
                         WHEN status = 'pending' THEN 2
                         WHEN status = 'failed' THEN 3
                         ELSE 4 END,
                    priority ASC, created_at DESC
                OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
            """
            
            cursor.execute(query, params + [offset, limit])
            rows = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            # Format jobs
            jobs = []
            for row in rows:
                job_data = {
                    'job_id': row[0],
                    'job_type': row[1],
                    'job_data': json.loads(row[2] or '{}'),
                    'status': row[3],
                    'priority': row[4],
                    'attempts': row[5],
                    'max_attempts': row[6],
                    'created_at': row[7].isoformat() if row[7] else None,
                    'started_at': row[8].isoformat() if row[8] else None,
                    'completed_at': row[9].isoformat() if row[9] else None,
                    'error_message': row[10],
                    'result_data': json.loads(row[11] or '{}') if row[11] else None,
                    'user_id': row[12]
                }
                jobs.append(job_data)
            
            return jsonify({
                'success': True,
                'jobs': jobs,
                'total': total_count,
                'limit': limit,
                'offset': offset,
                'has_more': offset + limit < total_count
            })
            
        except Exception as e:
            logger.error(f"Error getting job queue: {e}")
            return jsonify({
                'success': False,
                'message': f'Error getting job queue: {str(e)}'
            }), 500
    
    def retry_job(self, job_id):
        """Retry failed job"""
        try:
            job = self.job_service.get_job(job_id)
            
            if not job:
                return jsonify({
                    'success': False,
                    'message': 'Job not found'
                }), 404
            
            # Check if job can be retried
            if job.status != JobStatus.FAILED:
                return jsonify({
                    'success': False,
                    'message': f'Cannot retry job with status: {job.status.value}'
                }), 400
            
            if job.attempts >= job.max_attempts:
                return jsonify({
                    'success': False,
                    'message': 'Job has reached maximum retry attempts'
                }), 400
            
            # Check user permissions
            user_id = session.get('user_id', 'system')
            if job.user_id != user_id and user_id != 'admin':
                return jsonify({
                    'success': False,
                    'message': 'Not authorized to retry this job'
                }), 403
            
            # Reset job to pending status
            self.job_service.update_job_status(job_id, JobStatus.PENDING)
            
            logger.info(f"Retried job {job_id} by user {user_id}")
            
            return jsonify({
                'success': True,
                'message': 'Job retry initiated',
                'job_id': job_id
            })
            
        except Exception as e:
            logger.error(f"Error retrying job {job_id}: {e}")
            return jsonify({
                'success': False,
                'message': f'Error retrying job: {str(e)}'
            }), 500

    def mark_notification_read(self, notification_id):
        """Mark notification sebagai read"""
        try:
            user_id = session.get('user_id', 'system')
            
            from config.database import db_manager
            conn = db_manager.get_sqlserver_connection()
            if not conn:
                return jsonify({
                    'success': False,
                    'message': 'Database connection failed'
                }), 500
            
            cursor = conn.cursor()
            
            # Update notification
            update_query = """
                UPDATE job_notifications 
                SET is_read = 1, read_at = GETDATE()
                WHERE notification_id = ? AND user_id = ?
            """
            
            cursor.execute(update_query, (notification_id, user_id))
            rows_affected = cursor.rowcount
            
            conn.commit()
            cursor.close()
            conn.close()
            
            if rows_affected == 0:
                return jsonify({
                    'success': False,
                    'message': 'Notification not found or not authorized'
                }), 404
            
            return jsonify({
                'success': True,
                'message': 'Notification marked as read'
            })
            
        except Exception as e:
            logger.error(f"Error marking notification read: {e}")
            return jsonify({
                'success': False,
                'message': f'Error updating notification: {str(e)}'
            }), 500
    
    def get_job_history(self):
        """Get job history dengan filtering dan pagination"""
        try:
            # Get query parameters
            status = request.args.get('status')
            priority = request.args.get('priority')
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            search = request.args.get('search')
            page = request.args.get('page', 1, type=int)
            limit = request.args.get('limit', 50, type=int)
            
            # Validate parameters
            if page < 1:
                page = 1
            if limit < 1 or limit > 200:
                limit = 50
            
            offset = (page - 1) * limit
            
            # Get database connection
            from config.database import db_manager
            conn = db_manager.get_sqlserver_connection()
            if not conn:
                return jsonify({
                    'success': False,
                    'message': 'Database connection failed'
                }), 500
            
            cursor = conn.cursor()
            
            # Build WHERE clause
            where_conditions = ["status IN ('completed', 'failed', 'cancelled')"]
            params = []
            
            if status and status != '':
                where_conditions.append("status = ?")
                params.append(status)
            
            if priority and priority != '':
                where_conditions.append("priority = ?")
                params.append(int(priority))
            
            if start_date and start_date != '':
                where_conditions.append("CAST(created_at AS DATE) >= ?")
                params.append(start_date)
            
            if end_date and end_date != '':
                where_conditions.append("CAST(created_at AS DATE) <= ?")
                params.append(end_date)
            
            if search and search != '':
                where_conditions.append("(job_type LIKE ? OR job_data LIKE ?)")
                search_param = f"%{search}%"
                params.extend([search_param, search_param])
            
            where_clause = " AND ".join(where_conditions)
            
            # Get total count
            count_query = f"SELECT COUNT(*) FROM job_queue WHERE {where_clause}"
            cursor.execute(count_query, params)
            total_count = cursor.fetchone()[0]
            
            # Calculate pagination
            total_pages = (total_count + limit - 1) // limit
            
            # Get jobs with pagination
            query = f"""
                SELECT job_id, job_type, job_data, status, priority, attempts, 
                       max_attempts, created_at, started_at, completed_at, 
                       error_message, result_data, user_id
                FROM job_queue 
                WHERE {where_clause}
                ORDER BY completed_at DESC, created_at DESC
                OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
            """
            
            cursor.execute(query, params + [offset, limit])
            rows = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            # Format jobs
            jobs = []
            for row in rows:
                job_data = {
                    'id': row[0],
                    'job_name': row[1],
                    'job_data': row[2],
                    'status': row[3],
                    'priority': self._get_priority_text(row[4]),
                    'attempts': row[5],
                    'max_attempts': row[6],
                    'created_at': row[7].isoformat() if row[7] else None,
                    'started_at': row[8].isoformat() if row[8] else None,
                    'completed_at': row[9].isoformat() if row[9] else None,
                    'result': row[10] or (json.loads(row[11] or '{}').get('message', 'No result') if row[11] else 'No result'),
                    'user_id': row[12]
                }
                jobs.append(job_data)
            
            # Pagination info
            pagination = {
                'current_page': page,
                'total_pages': total_pages,
                'total_items': total_count,
                'has_prev': page > 1,
                'has_next': page < total_pages,
                'prev_page': page - 1 if page > 1 else None,
                'next_page': page + 1 if page < total_pages else None
            }
            
            return jsonify({
                'success': True,
                'data': {
                    'jobs': jobs,
                    'pagination': pagination
                }
            })
            
        except Exception as e:
            logger.error(f"Error getting job history: {e}")
            return jsonify({
                'success': False,
                'message': f'Error getting job history: {str(e)}'
            }), 500
    
    def get_job_history_stats(self):
        """Get job history statistics"""
        try:
            # Get query parameters for filtering
            status = request.args.get('status')
            priority = request.args.get('priority')
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            search = request.args.get('search')
            
            # Get database connection
            from config.database import db_manager
            conn = db_manager.get_sqlserver_connection()
            if not conn:
                return jsonify({
                    'success': False,
                    'message': 'Database connection failed'
                }), 500
            
            cursor = conn.cursor()
            
            # Build WHERE clause for filtering
            where_conditions = ["status IN ('completed', 'failed', 'cancelled')"]
            params = []
            
            if status and status != '':
                where_conditions.append("status = ?")
                params.append(status)
            
            if priority and priority != '':
                where_conditions.append("priority = ?")
                params.append(int(priority))
            
            if start_date and start_date != '':
                where_conditions.append("CAST(created_at AS DATE) >= ?")
                params.append(start_date)
            
            if end_date and end_date != '':
                where_conditions.append("CAST(created_at AS DATE) <= ?")
                params.append(end_date)
            
            if search and search != '':
                where_conditions.append("(job_type LIKE ? OR job_data LIKE ?)")
                search_param = f"%{search}%"
                params.extend([search_param, search_param])
            
            where_clause = " AND ".join(where_conditions)
            
            # Get status counts
            stats_query = f"""
                SELECT 
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                    SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) as cancelled,
                    AVG(CASE 
                        WHEN status = 'completed' AND started_at IS NOT NULL AND completed_at IS NOT NULL 
                        THEN DATEDIFF(second, started_at, completed_at)
                        ELSE NULL 
                    END) as avg_duration
                FROM job_queue 
                WHERE {where_clause}
            """
            
            cursor.execute(stats_query, params)
            stats_row = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            stats = {
                'completed': int(stats_row[0] or 0),
                'failed': int(stats_row[1] or 0),
                'cancelled': int(stats_row[2] or 0),
                'avg_duration': round(float(stats_row[3] or 0), 1)
            }
            
            return jsonify({
                'success': True,
                'data': stats
            })
            
        except Exception as e:
            logger.error(f"Error getting job history stats: {e}")
            return jsonify({
                'success': False,
                'message': f'Error getting job history stats: {str(e)}'
            }), 500
    
    def get_job_details(self, job_id):
        """Get detailed information about a specific job"""
        try:
            # Get database connection
            from config.database import db_manager
            conn = db_manager.get_sqlserver_connection()
            if not conn:
                return jsonify({
                    'success': False,
                    'message': 'Database connection failed'
                }), 500
            
            cursor = conn.cursor()
            
            # Get job details
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
            
            if not row:
                return jsonify({
                    'success': False,
                    'message': 'Job not found'
                }), 404
            
            # Format job details
            job_details = {
                'id': row[0],
                'job_name': row[1],
                'job_data': row[2],
                'status': row[3],
                'priority': self._get_priority_text(row[4]),
                'attempts': row[5],
                'max_attempts': row[6],
                'created_at': row[7].isoformat() if row[7] else None,
                'started_at': row[8].isoformat() if row[8] else None,
                'completed_at': row[9].isoformat() if row[9] else None,
                'result': row[10] or (json.loads(row[11] or '{}').get('message', 'No result') if row[11] else 'No result'),
                'user_id': row[12]
            }
            
            return jsonify({
                'success': True,
                'data': job_details
            })
            
        except Exception as e:
            logger.error(f"Error getting job details {job_id}: {e}")
            return jsonify({
                'success': False,
                'message': f'Error getting job details: {str(e)}'
            }), 500
    
    def export_job_history(self):
        """Export job history to CSV"""
        try:
            from flask import Response
            import csv
            import io
            
            # Get query parameters for filtering
            status = request.args.get('status')
            priority = request.args.get('priority')
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            search = request.args.get('search')
            
            # Get database connection
            from config.database import db_manager
            conn = db_manager.get_sqlserver_connection()
            if not conn:
                return jsonify({
                    'success': False,
                    'message': 'Database connection failed'
                }), 500
            
            cursor = conn.cursor()
            
            # Build WHERE clause for filtering
            where_conditions = ["status IN ('completed', 'failed', 'cancelled')"]
            params = []
            
            if status and status != '':
                where_conditions.append("status = ?")
                params.append(status)
            
            if priority and priority != '':
                where_conditions.append("priority = ?")
                params.append(int(priority))
            
            if start_date and start_date != '':
                where_conditions.append("CAST(created_at AS DATE) >= ?")
                params.append(start_date)
            
            if end_date and end_date != '':
                where_conditions.append("CAST(created_at AS DATE) <= ?")
                params.append(end_date)
            
            if search and search != '':
                where_conditions.append("(job_type LIKE ? OR job_data LIKE ?)")
                search_param = f"%{search}%"
                params.extend([search_param, search_param])
            
            where_clause = " AND ".join(where_conditions)
            
            # Get all matching jobs
            query = f"""
                SELECT job_id, job_type, job_data, status, priority, attempts, 
                       max_attempts, created_at, started_at, completed_at, 
                       error_message, result_data, user_id
                FROM job_queue 
                WHERE {where_clause}
                ORDER BY completed_at DESC, created_at DESC
            """
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            # Create CSV output
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow([
                'Job ID', 'Job Name', 'Status', 'Priority', 'Attempts', 'Max Attempts',
                'Created', 'Started', 'Completed', 'Duration (seconds)', 'Result', 'User ID'
            ])
            
            # Write data rows
            for row in rows:
                duration = ''
                if row[8] and row[9]:  # started_at and completed_at
                    start_time = row[8]
                    end_time = row[9]
                    duration_seconds = (end_time - start_time).total_seconds()
                    duration = str(int(duration_seconds))
                
                result = row[10] or (json.loads(row[11] or '{}').get('message', 'No result') if row[11] else 'No result')
                
                writer.writerow([
                    row[0],  # job_id
                    row[1],  # job_type
                    row[3],  # status
                    self._get_priority_text(row[4]),  # priority
                    row[5],  # attempts
                    row[6],  # max_attempts
                    row[7].isoformat() if row[7] else '',  # created_at
                    row[8].isoformat() if row[8] else '',  # started_at
                    row[9].isoformat() if row[9] else '',  # completed_at
                    duration,
                    result,
                    row[12]  # user_id
                ])
            
            # Prepare response
            output.seek(0)
            filename = f"job_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            
            response = Response(
                output.getvalue(),
                mimetype='text/csv',
                headers={'Content-Disposition': f'attachment; filename={filename}'}
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Error exporting job history: {e}")
            return jsonify({
                'success': False,
                'message': f'Error exporting job history: {str(e)}'
            }), 500
    
    def get_job_statistics_advanced(self):
        """Get comprehensive job statistics with charts and analytics data"""
        try:
            # Get query parameters for filtering
            time_range = request.args.get('timeRange', 'week')
            job_type = request.args.get('jobType', '')
            
            # Get database connection
            from config.database import db_manager
            conn = db_manager.get_sqlserver_connection()
            if not conn:
                return jsonify({
                    'success': False,
                    'message': 'Database connection failed'
                }), 500
            
            cursor = conn.cursor()
            
            # Build date filter based on time range
            date_filter = self._get_date_filter(time_range)
            
            # Build WHERE clause
            where_conditions = [f"created_at >= {date_filter}"]
            params = []
            
            if job_type and job_type != '':
                where_conditions.append("job_type = ?")
                params.append(job_type)
            
            where_clause = " AND ".join(where_conditions)
            
            # Get overall statistics
            overview_query = f"""
                SELECT 
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                    SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) as cancelled,
                    AVG(CASE 
                        WHEN status = 'completed' AND started_at IS NOT NULL AND completed_at IS NOT NULL 
                        THEN DATEDIFF(second, started_at, completed_at)
                        ELSE NULL 
                    END) as avg_duration,
                    COUNT(*) as total
                FROM job_queue 
                WHERE {where_clause}
            """
            
            cursor.execute(overview_query, params)
            overview_row = cursor.fetchone()
            
            completed = int(overview_row[0] or 0)
            failed = int(overview_row[1] or 0)
            cancelled = int(overview_row[2] or 0)
            avg_duration = round(float(overview_row[3] or 0), 1)
            total = int(overview_row[4] or 0)
            
            success_rate = round((completed / total * 100) if total > 0 else 0, 1)
            
            # Get duration distribution
            duration_query = f"""
                SELECT 
                    SUM(CASE WHEN duration <= 30 THEN 1 ELSE 0 END) as under_30s,
                    SUM(CASE WHEN duration > 30 AND duration <= 60 THEN 1 ELSE 0 END) as s30_to_1m,
                    SUM(CASE WHEN duration > 60 AND duration <= 300 THEN 1 ELSE 0 END) as m1_to_5m,
                    SUM(CASE WHEN duration > 300 AND duration <= 900 THEN 1 ELSE 0 END) as m5_to_15m,
                    SUM(CASE WHEN duration > 900 THEN 1 ELSE 0 END) as over_15m
                FROM (
                    SELECT 
                        CASE 
                            WHEN started_at IS NOT NULL AND completed_at IS NOT NULL 
                            THEN DATEDIFF(second, started_at, completed_at)
                            ELSE NULL 
                        END as duration
                    FROM job_queue 
                    WHERE {where_clause} AND status = 'completed'
                ) t
                WHERE duration IS NOT NULL
            """
            
            cursor.execute(duration_query, params)
            duration_row = cursor.fetchone()
            
            duration_distribution = {
                '0-30s': int(duration_row[0] or 0),
                '30s-1m': int(duration_row[1] or 0),
                '1-5m': int(duration_row[2] or 0),
                '5-15m': int(duration_row[3] or 0),
                '15m+': int(duration_row[4] or 0)
            }
            
            # Get performance metrics
            performance_query = f"""
                SELECT 
                    AVG(CASE 
                        WHEN started_at IS NOT NULL 
                        THEN DATEDIFF(second, created_at, started_at)
                        ELSE NULL 
                    END) as avg_wait_time,
                    AVG(CAST(attempts as FLOAT)) as avg_retries,
                    COUNT(*) * 1.0 / NULLIF(DATEDIFF(hour, MIN(created_at), MAX(created_at)), 0) as throughput
                FROM job_queue 
                WHERE {where_clause}
            """
            
            cursor.execute(performance_query, params)
            performance_row = cursor.fetchone()
            
            avg_wait_time = round(float(performance_row[0] or 0), 1)
            avg_retries = round(float(performance_row[1] or 0), 2)
            throughput = round(float(performance_row[2] or 0), 1)
            
            # Get peak hour
            peak_hour_query = f"""
                SELECT TOP 1 DATEPART(hour, created_at) as hour, COUNT(*) as count
                FROM job_queue 
                WHERE {where_clause}
                GROUP BY DATEPART(hour, created_at)
                ORDER BY count DESC
            """
            
            cursor.execute(peak_hour_query, params)
            peak_hour_row = cursor.fetchone()
            peak_hour = f"{int(peak_hour_row[0]):02d}:00" if peak_hour_row else "--:--"
            
            # Get top job types
            top_types_query = f"""
                SELECT TOP 5 job_type, COUNT(*) as count,
                       CAST(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER() AS DECIMAL(5,1)) as percentage
                FROM job_queue 
                WHERE {where_clause}
                GROUP BY job_type
                ORDER BY count DESC
            """
            
            cursor.execute(top_types_query, params)
            top_types_rows = cursor.fetchall()
            
            top_job_types = []
            for row in top_types_rows:
                top_job_types.append({
                    'job_type': row[0],
                    'count': int(row[1]),
                    'percentage': float(row[2])
                })
            
            # Get common error types
            error_query = f"""
                SELECT TOP 5 
                    CASE 
                        WHEN error_message LIKE '%timeout%' THEN 'Timeout Error'
                        WHEN error_message LIKE '%connection%' THEN 'Connection Error'
                        WHEN error_message LIKE '%permission%' THEN 'Permission Error'
                        WHEN error_message LIKE '%database%' THEN 'Database Error'
                        ELSE 'Other Error'
                    END as error_type,
                    COUNT(*) as count,
                    CAST(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER() AS DECIMAL(5,1)) as percentage
                FROM job_queue 
                WHERE {where_clause} AND status = 'failed' AND error_message IS NOT NULL
                GROUP BY 
                    CASE 
                        WHEN error_message LIKE '%timeout%' THEN 'Timeout Error'
                        WHEN error_message LIKE '%connection%' THEN 'Connection Error'
                        WHEN error_message LIKE '%permission%' THEN 'Permission Error'
                        WHEN error_message LIKE '%database%' THEN 'Database Error'
                        ELSE 'Other Error'
                    END
                ORDER BY count DESC
            """
            
            cursor.execute(error_query, params)
            error_rows = cursor.fetchall()
            
            common_errors = []
            for row in error_rows:
                common_errors.append({
                    'error_type': row[0],
                    'count': int(row[1]),
                    'percentage': float(row[2])
                })
            
            # Get trend data (last 7 days)
            trend_query = f"""
                SELECT 
                    CAST(created_at AS DATE) as date,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
                FROM job_queue 
                WHERE created_at >= DATEADD(day, -7, GETDATE())
                {' AND job_type = ?' if job_type else ''}
                GROUP BY CAST(created_at AS DATE)
                ORDER BY date
            """
            
            trend_params = [job_type] if job_type else []
            cursor.execute(trend_query, trend_params)
            trend_rows = cursor.fetchall()
            
            trend_data = {
                'labels': [],
                'completed': [],
                'failed': []
            }
            
            for row in trend_rows:
                trend_data['labels'].append(row[0].strftime('%Y-%m-%d'))
                trend_data['completed'].append(int(row[1]))
                trend_data['failed'].append(int(row[2]))
            
            cursor.close()
            conn.close()
            
            # Build response
            statistics = {
                'overview': {
                    'completed': completed,
                    'failed': failed,
                    'cancelled': cancelled,
                    'total': total,
                    'avg_duration': avg_duration,
                    'success_rate': success_rate
                },
                'trends': {
                    'completed_trend': 5.2,  # Mock data - you can calculate real trends
                    'failed_trend': -2.1,
                    'duration_trend': -0.8,
                    'success_rate_trend': 3.5
                },
                'duration_distribution': duration_distribution,
                'performance': {
                    'avg_wait_time': avg_wait_time,
                    'avg_retries': avg_retries,
                    'throughput': throughput,
                    'peak_hour': peak_hour
                },
                'top_job_types': top_job_types,
                'common_errors': common_errors,
                'trend_data': trend_data
            }
            
            return jsonify({
                'success': True,
                'data': statistics
            })
            
        except Exception as e:
            logger.error(f"Error getting job statistics: {e}")
            return jsonify({
                'success': False,
                'message': f'Error getting job statistics: {str(e)}'
            }), 500
    
    def get_job_trends(self):
        """Get job trends data for chart visualization"""
        try:
            # Get query parameters
            time_range = request.args.get('timeRange', 'week')
            job_type = request.args.get('jobType', '')
            period = request.args.get('period', 'daily')
            
            # Get database connection
            from config.database import db_manager
            conn = db_manager.get_sqlserver_connection()
            if not conn:
                return jsonify({
                    'success': False,
                    'message': 'Database connection failed'
                }), 500
            
            cursor = conn.cursor()
            
            # Build date filter and grouping based on period
            date_filter = self._get_date_filter(time_range)
            
            if period == 'hourly':
                group_by = "FORMAT(created_at, 'yyyy-MM-dd HH')"
                order_by = "FORMAT(created_at, 'yyyy-MM-dd HH')"
            elif period == 'weekly':
                group_by = "FORMAT(created_at, 'yyyy-\\WW')"
                order_by = "FORMAT(created_at, 'yyyy-\\WW')"
            else:  # daily
                group_by = "CAST(created_at AS DATE)"
                order_by = "CAST(created_at AS DATE)"
            
            # Build WHERE clause
            where_conditions = [f"created_at >= {date_filter}"]
            params = []
            
            if job_type and job_type != '':
                where_conditions.append("job_type = ?")
                params.append(job_type)
            
            where_clause = " AND ".join(where_conditions)
            
            # Get trend data
            query = f"""
                SELECT 
                    {group_by} as period,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
                FROM job_queue 
                WHERE {where_clause}
                GROUP BY {group_by}
                ORDER BY {order_by}
            """
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            # Format data
            trend_data = {
                'labels': [],
                'completed': [],
                'failed': []
            }
            
            for row in rows:
                if period == 'hourly':
                    label = f"{row[0]}:00"
                elif period == 'weekly':
                    label = f"Week {row[0]}"
                else:
                    label = str(row[0])
                
                trend_data['labels'].append(label)
                trend_data['completed'].append(int(row[1]))
                trend_data['failed'].append(int(row[2]))
            
            return jsonify({
                'success': True,
                'data': trend_data
            })
            
        except Exception as e:
            logger.error(f"Error getting job trends: {e}")
            return jsonify({
                'success': False,
                'message': f'Error getting job trends: {str(e)}'
            }), 500
    
    def _get_date_filter(self, time_range):
        """Get SQL date filter based on time range"""
        filters = {
            'today': "CAST(GETDATE() AS DATE)",
            'yesterday': "DATEADD(day, -1, CAST(GETDATE() AS DATE))",
            'week': "DATEADD(day, -7, GETDATE())",
            'month': "DATEADD(day, -30, GETDATE())",
            'quarter': "DATEADD(day, -90, GETDATE())",
            'year': "DATEADD(year, -1, GETDATE())"
        }
        
        return filters.get(time_range, filters['week'])
    
    def _get_priority_text(self, priority_num):
        """Convert priority number to text"""
        if priority_num <= 3:
            return 'high'
        elif priority_num <= 7:
            return 'medium'
        else:
            return 'low'
    
    def _get_result_summary(self, job):
        """Get summary dari job result untuk display"""
        try:
            if not job.result_data:
                return None
            
            if job.job_type == JobType.PROCEDURE_PROCESSING.value:
                result_data = job.result_data
                total_procedures = len(result_data.get('procedures', {}))
                successful_procedures = sum(1 for p in result_data.get('procedures', {}).values() 
                                          if p.get('success', False))
                
                return {
                    'overall_success': result_data.get('success', False),
                    'total_procedures': total_procedures,
                    'successful_procedures': successful_procedures,
                    'target_date': result_data.get('target_date'),
                    'processed_at': result_data.get('processed_at')
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting result summary: {e}")
            return None
    
    def start_job_worker(self):
        """Start job worker"""
        try:
            if self.job_service.is_running:
                return jsonify({
                    'success': False,
                    'message': 'Job worker is already running'
                })
            
            self.job_service.start_worker()
            logger.info("Job worker started manually")
            
            return jsonify({
                'success': True,
                'message': 'Job worker started successfully',
                'status': 'running'
            })
            
        except Exception as e:
            logger.error(f"Error starting job worker: {e}")
            return jsonify({
                'success': False,
                'message': f'Error starting worker: {str(e)}'
            }), 500
    
    def stop_job_worker(self):
        """Stop job worker"""
        try:
            if not self.job_service.is_running:
                return jsonify({
                    'success': False,
                    'message': 'Job worker is not running'
                })
            
            self.job_service.stop_worker()
            logger.info("Job worker stopped manually")
            
            return jsonify({
                'success': True,
                'message': 'Job worker stopped successfully',
                'status': 'stopped'
            })
            
        except Exception as e:
            logger.error(f"Error stopping job worker: {e}")
            return jsonify({
                'success': False,
                'message': f'Error stopping worker: {str(e)}'
            }), 500
    
    def restart_job_worker(self):
        """Restart job worker"""
        try:
            # Stop if running
            if self.job_service.is_running:
                self.job_service.stop_worker()
                logger.info("Job worker stopped for restart")
            
            # Start worker
            self.job_service.start_worker()
            logger.info("Job worker restarted manually")
            
            return jsonify({
                'success': True,
                'message': 'Job worker restarted successfully',
                'status': 'running'
            })
            
        except Exception as e:
            logger.error(f"Error restarting job worker: {e}")
            return jsonify({
                'success': False,
                'message': f'Error restarting worker: {str(e)}'
            }), 500
    
    def get_worker_status(self):
        """Get job worker status"""
        try:
            stats = self.job_service.get_job_statistics()
            
            return jsonify({
                'success': True,
                'worker_status': {
                    'is_running': self.job_service.is_running,
                    'status': 'running' if self.job_service.is_running else 'stopped',
                    'thread_alive': self.job_service.worker_thread.is_alive() if self.job_service.worker_thread else False,
                    'registered_handlers': list(self.job_service.job_handlers.keys()),
                    'statistics': stats
                }
            })
            
        except Exception as e:
            logger.error(f"Error getting worker status: {e}")
            return jsonify({
                'success': False,
                'message': f'Error getting worker status: {str(e)}'
            }), 500
    
    def create_test_job(self):
        """Create a test job for debugging"""
        try:
            from datetime import datetime
            
            # Get user info from session
            user_id = session.get('user_id', 'test_user')
            
            # Create test job data
            test_date = datetime.now().strftime('%Y-%m-%d')
            job_data = {
                'target_date': test_date,
                'procedures': ['attrecord'],
                'requested_by': user_id,
                'request_time': datetime.now().isoformat(),
                'source': 'test_job_creation'
            }
            
            # Create job
            job_id = self.job_service.create_job(
                job_type=JobType.PROCEDURE_PROCESSING.value,
                job_data=job_data,
                user_id=user_id,
                priority=8  # Low priority for testing
            )
            
            logger.info(f"Created test job {job_id} by user {user_id}")
            
            return jsonify({
                'success': True,
                'message': 'Test job created successfully',
                'job_id': job_id,
                'job_data': job_data
            })
            
        except Exception as e:
            logger.error(f"Error creating test job: {e}")
            return jsonify({
                'success': False,
                'message': f'Error creating test job: {str(e)}'
            }), 500

# Global controller instance
job_controller = JobController()