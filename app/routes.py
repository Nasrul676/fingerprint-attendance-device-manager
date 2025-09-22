from flask import Blueprint, redirect, url_for
from app.controllers.main_controller import MainController
from app.controllers.api_controller import APIController
from app.controllers.sync_controller import SyncController
from app.controllers.fplog_controller import FPLogController
from app.controllers.failed_log_controller import FailedLogController
from app.controllers.worker_controller import worker_bp
from app.controllers.job_controller import job_controller

# Create blueprints
main_bp = Blueprint('main', __name__)
api_bp = Blueprint('api', __name__)
sync_bp = Blueprint('sync', __name__, url_prefix='/sync')
fplog_bp = Blueprint('fplog', __name__, url_prefix='/fplog')
failed_logs_bp = Blueprint('failed_logs', __name__, url_prefix='/failed-logs')
job_bp = Blueprint('job', __name__, url_prefix='/job')

# Initialize controllers
main_controller = MainController()
api_controller = APIController()
sync_controller = SyncController()
fplog_controller = FPLogController()
failed_log_controller = FailedLogController()

# Main routes
@main_bp.route('/')
def index():
    return redirect(url_for('fplog.fplog_dashboard'))

@main_bp.route('/export')
def export_csv():
    return main_controller.export_csv()

# API routes
@api_bp.route('/attrecord', methods=['POST'])
def api_attrecord():
    return api_controller.api_attrecord_post()

@api_bp.route('/spjamkerja', methods=['POST'])
def api_spjamkerja():
    return api_controller.api_spjamkerja_post()

@api_bp.route('/streaming/start', methods=['POST'])
def api_streaming_start():
    return api_controller.api_streaming_start()

@api_bp.route('/streaming/stop', methods=['POST'])
def api_streaming_stop():
    return api_controller.api_streaming_stop()

@api_bp.route('/streaming/status', methods=['GET'])
def api_streaming_status():
    return api_controller.api_streaming_status()

@api_bp.route('/summary', methods=['GET'])
def api_summary():
    return api_controller.api_summary()

# Sync routes
@sync_bp.route('/')
def sync_dashboard():
    return sync_controller.sync_dashboard()

@sync_bp.route('/start', methods=['POST'])
def start_sync_all():
    return sync_controller.start_sync_all()

@sync_bp.route('/device/<device_name>/start', methods=['POST'])
def start_sync_device(device_name):
    return sync_controller.start_sync_device(device_name)

@sync_bp.route('/status')
def sync_status():
    return sync_controller.get_sync_status()

@sync_bp.route('/cancel', methods=['POST'])
def cancel_sync():
    return sync_controller.cancel_sync()

@sync_bp.route('/devices')
def device_list():
    return sync_controller.get_device_list()

@sync_bp.route('/summary')
def sync_summary():
    return sync_controller.get_sync_summary()

@sync_bp.route('/history')
def sync_history():
    return sync_controller.sync_history()

@sync_bp.route('/device/<device_name>/test', methods=['POST'])
def test_device_connection(device_name):
    return sync_controller.test_device_connection(device_name)

# Streaming routes
@sync_bp.route('/streaming/start', methods=['POST'])
def start_streaming():
    return sync_controller.start_streaming()

@sync_bp.route('/streaming/stop', methods=['POST'])
def stop_streaming():
    return sync_controller.stop_streaming()

@sync_bp.route('/streaming/status')
def get_streaming_status():
    return sync_controller.get_streaming_status()

@sync_bp.route('/streaming/notifications')
def get_streaming_notifications():
    return sync_controller.get_streaming_notifications()

@sync_bp.route('/streaming/notifications/clear', methods=['POST'])
def clear_streaming_notifications():
    return sync_controller.clear_streaming_notifications()

# FPLog routes
@fplog_bp.route('/')
def fplog_dashboard():
    return fplog_controller.fplog_dashboard()

@fplog_bp.route('/search', methods=['POST'])
def search_fplog():
    return fplog_controller.search_fplog()

@fplog_bp.route('/export', methods=['POST'])
def export_fplog_excel():
    return fplog_controller.export_fplog_excel()

@fplog_bp.route('/stats')
def get_fplog_stats():
    return fplog_controller.get_fplog_stats()

# Failed Logs routes
@failed_logs_bp.route('/')
def failed_logs_dashboard():
    return failed_log_controller.failed_logs_dashboard()

@failed_logs_bp.route('/search', methods=['POST'])
def search_failed_logs():
    return failed_log_controller.search_failed_logs()

@failed_logs_bp.route('/stats')
def get_failed_logs_stats():
    return failed_log_controller.get_failed_logs_stats()

# Job Management routes
@job_bp.route('/')
def job_dashboard():
    from flask import render_template
    return render_template('job_dashboard_enhanced.html')

@job_bp.route('/queue')
def job_queue_monitor():
    from flask import render_template
    return render_template('job_queue_monitor.html')

@job_bp.route('/history')
def job_history():
    from flask import render_template
    return render_template('job_history.html')

@job_bp.route('/statistics')
def job_statistics():
    from flask import render_template
    return render_template('job_statistics.html')

@job_bp.route('/procedure', methods=['POST'])
def create_procedure_job():
    return job_controller.create_procedure_job()

@job_bp.route('/<job_id>/status', methods=['GET'])
def get_job_status(job_id):
    return job_controller.get_job_status(job_id)

@job_bp.route('/user', methods=['GET'])
def get_user_jobs():
    return job_controller.get_user_jobs()

@job_bp.route('/queue/api', methods=['GET'])
def get_job_queue():
    return job_controller.get_job_queue()

@job_bp.route('/statistics/api', methods=['GET'])
def get_job_statistics():
    return job_controller.get_job_statistics()

@job_bp.route('/<job_id>/cancel', methods=['POST'])
def cancel_job(job_id):
    return job_controller.cancel_job(job_id)

@job_bp.route('/notifications', methods=['GET'])
def get_job_notifications():
    return job_controller.get_job_notifications()

@job_bp.route('/notifications/<notification_id>/read', methods=['POST'])
def mark_notification_read(notification_id):
    return job_controller.mark_notification_read(notification_id)

@job_bp.route('/<job_id>/retry', methods=['POST'])
def retry_job(job_id):
    return job_controller.retry_job(job_id)

# Job History API routes
@job_bp.route('/api/job-history', methods=['GET'])
def get_job_history():
    return job_controller.get_job_history()

@job_bp.route('/api/job-history-stats', methods=['GET'])
def get_job_history_stats():
    return job_controller.get_job_history_stats()

@job_bp.route('/api/job-details/<job_id>', methods=['GET'])
def get_job_details(job_id):
    return job_controller.get_job_details(job_id)

@job_bp.route('/api/job-history-export', methods=['GET'])
def export_job_history():
    return job_controller.export_job_history()

@job_bp.route('/api/retry-job/<job_id>', methods=['POST'])
def retry_job_api(job_id):
    return job_controller.retry_job(job_id)

# Job Statistics API routes
@job_bp.route('/api/job-statistics', methods=['GET'])
def get_job_statistics_advanced():
    return job_controller.get_job_statistics_advanced()

@job_bp.route('/api/job-trends', methods=['GET'])
def get_job_trends():
    return job_controller.get_job_trends()

# Worker Control API routes
@job_bp.route('/worker/start', methods=['POST'])
def start_job_worker():
    return job_controller.start_job_worker()

@job_bp.route('/worker/stop', methods=['POST'])
def stop_job_worker():
    return job_controller.stop_job_worker()

@job_bp.route('/worker/restart', methods=['POST'])
def restart_job_worker():
    return job_controller.restart_job_worker()

@job_bp.route('/worker/status', methods=['GET'])
def get_worker_status():
    return job_controller.get_worker_status()

@job_bp.route('/test-job', methods=['POST'])
def create_test_job():
    return job_controller.create_test_job()
