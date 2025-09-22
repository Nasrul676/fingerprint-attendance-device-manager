"""
Controller untuk mengelola Attendance Worker dan eksekusi manual
"""
from flask import Blueprint, render_template, request, flash, redirect, url_for, session, jsonify
from app.models.worker_model import WorkerModel
from app.services.job_service import job_service, JobType
from datetime import datetime, timedelta

# Create blueprint for worker management
worker_bp = Blueprint('worker', __name__, url_prefix='/worker')

@worker_bp.route('/dashboard')
def worker_dashboard():
    """Menampilkan halaman untuk eksekusi prosedur manual."""
    today = datetime.today().strftime('%Y-%m-%d')
    return render_template('worker/dashboard.html', default_date=today)

@worker_bp.route('/run-manual', methods=['POST'])
def run_procedures_manual():
    """Menjalankan prosedur attrecord dan spJamkerja untuk rentang tanggal melalui job queue."""
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    
    if not start_date or not end_date:
        flash('Start date and end date are required.', 'danger')
        return redirect(url_for('worker.worker_dashboard'))
        
    try:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')

        if start_dt > end_dt:
            flash('Start date cannot be after end date.', 'danger')
            return redirect(url_for('worker.worker_dashboard'))

        # Get user info from session
        user_id = session.get('user_id', 'manual_user')
        
        # Create job for each date in the range
        jobs_created = []
        current_date = start_dt
        
        while current_date <= end_dt:
            date_str = current_date.strftime('%Y-%m-%d')
            
            # Create job data
            job_data = {
                'target_date': date_str,
                'procedures': ['attrecord', 'spjamkerja'],
                'requested_by': user_id,
                'request_time': datetime.now().isoformat(),
                'source': 'manual_worker_dashboard'
            }
            
            # Create job
            job_id = job_service.create_job(
                job_type=JobType.PROCEDURE_PROCESSING.value,
                job_data=job_data,
                user_id=user_id,
                priority=5  # Normal priority
            )
            
            jobs_created.append({
                'job_id': job_id,
                'date': date_str
            })
            
            current_date = current_date + timedelta(days=1)
        
        # Flash success message
        job_count = len(jobs_created)
        flash(f'Successfully created {job_count} job(s) for date range {start_date} to {end_date}. '
              f'Jobs will be processed in background. Check Job Dashboard for progress.', 'success')

    except ValueError:
        flash('Invalid date format. Please use YYYY-MM-DD.', 'danger')
    except Exception as e:
        flash(f"An unexpected error occurred: {str(e)}", 'danger')

    return redirect(url_for('worker.worker_dashboard'))

@worker_bp.route('/run-manual-ajax', methods=['POST'])
def run_procedures_manual_ajax():
    """AJAX endpoint untuk menjalankan prosedur melalui job queue."""
    try:
        data = request.get_json()
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        if not start_date or not end_date:
            return jsonify({
                'success': False,
                'message': 'Start date and end date are required'
            }), 400
            
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')

        if start_dt > end_dt:
            return jsonify({
                'success': False,
                'message': 'Start date cannot be after end date'
            }), 400

        # Get user info from session
        user_id = session.get('user_id', 'manual_user')
        
        # Create job for each date in the range
        jobs_created = []
        current_date = start_dt
        
        while current_date <= end_dt:
            date_str = current_date.strftime('%Y-%m-%d')
            
            # Create job data
            job_data = {
                'target_date': date_str,
                'procedures': ['attrecord', 'spjamkerja'],
                'requested_by': user_id,
                'request_time': datetime.now().isoformat(),
                'source': 'manual_worker_dashboard'
            }
            
            # Create job
            job_id = job_service.create_job(
                job_type=JobType.PROCEDURE_PROCESSING.value,
                job_data=job_data,
                user_id=user_id,
                priority=5  # Normal priority
            )
            
            jobs_created.append({
                'job_id': job_id,
                'date': date_str
            })
            
            current_date = current_date + timedelta(days=1)
        
        return jsonify({
            'success': True,
            'message': f'Successfully created {len(jobs_created)} job(s) for processing',
            'jobs_created': jobs_created,
            'date_range': f'{start_date} to {end_date}'
        })
        
    except ValueError:
        return jsonify({
            'success': False,
            'message': 'Invalid date format. Please use YYYY-MM-DD'
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'An unexpected error occurred: {str(e)}'
        }), 500

# Helper function to register blueprint
def register_worker_blueprint(app):
    """Register worker blueprint dengan app"""
    app.register_blueprint(worker_bp)
