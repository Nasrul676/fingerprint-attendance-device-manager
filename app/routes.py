from flask import Blueprint, redirect, url_for
from app.controllers.main_controller import MainController
from app.controllers.api_controller import APIController
from app.controllers.sync_controller import SyncController
from app.controllers.fplog_controller import FPLogController
from app.controllers.failed_log_controller import FailedLogController
from app.controllers.vps_push_controller import vps_push_controller
from app.controllers.legacy_attendance_controller import legacy_attendance_controller

from app.controllers.attendance_worker_controller import attendance_worker_controller

# Create blueprints
main_bp = Blueprint('main', __name__)
api_bp = Blueprint('api', __name__)
sync_bp = Blueprint('sync', __name__, url_prefix='/sync')
fplog_bp = Blueprint('fplog', __name__, url_prefix='/fplog')
failed_logs_bp = Blueprint('failed_logs', __name__, url_prefix='/failed-logs')
vps_push_bp = Blueprint('vps_push', __name__, url_prefix='/vps-push')
legacy_attendance_bp = Blueprint('legacy_attendance', __name__, url_prefix='/legacy-attendance')

attendance_worker_bp = Blueprint('attendance_worker', __name__, url_prefix='/attendance-worker')

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

@sync_bp.route('/procedures/execute', methods=['POST'])
def execute_stored_procedures():
    return sync_controller.execute_stored_procedures()

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



# Attendance Worker routes
@attendance_worker_bp.route('/')
def attendance_worker_dashboard():
    return attendance_worker_controller.dashboard()

@attendance_worker_bp.route('/api/status')
def get_attendance_worker_status():
    return attendance_worker_controller.get_worker_status()

@attendance_worker_bp.route('/api/statistics')
def get_attendance_queue_statistics():
    return attendance_worker_controller.get_queue_statistics()

@attendance_worker_bp.route('/api/start', methods=['POST'])
def start_attendance_worker():
    return attendance_worker_controller.start_worker()

@attendance_worker_bp.route('/api/stop', methods=['POST'])
def stop_attendance_worker():
    return attendance_worker_controller.stop_worker()

@attendance_worker_bp.route('/api/run-now', methods=['POST'])
def run_attendance_worker_now():
    return attendance_worker_controller.run_now()

@attendance_worker_bp.route('/api/activity-log')
def get_attendance_worker_activity_log():
    return attendance_worker_controller.get_activity_log()

@attendance_worker_bp.route('/api/clear-log', methods=['POST'])
def clear_attendance_worker_activity_log():
    return attendance_worker_controller.clear_activity_log()

@attendance_worker_bp.route('/api/download-log')
def download_attendance_worker_log():
    return attendance_worker_controller.download_log()

# VPS Push routes
@vps_push_bp.route('/')
def vps_push_dashboard():
    """VPS Push Dashboard"""
    return vps_push_controller.dashboard()

@vps_push_bp.route('/test', methods=['GET'])
def test_vps_connection():
    """Test VPS connection"""
    return vps_push_controller.test_vps_connection()

@vps_push_bp.route('/statistics', methods=['GET'])
def get_vps_statistics():
    """Get VPS push statistics"""
    return vps_push_controller.get_vps_statistics()

@vps_push_bp.route('/preview', methods=['POST'])
def get_attrecord_preview():
    """Get preview of AttRecord data without pushing"""
    return vps_push_controller.get_attrecord_preview()

@vps_push_bp.route('/push/today', methods=['POST'])
def push_attrecord_today():
    """Push today's AttRecord data to VPS"""
    return vps_push_controller.push_attrecord_today()

@vps_push_bp.route('/push/date-range', methods=['POST'])
def push_attrecord_by_date():
    """Push AttRecord data by date range to VPS"""
    return vps_push_controller.push_attrecord_by_date()

@vps_push_bp.route('/push/pins', methods=['POST'])
def push_attrecord_for_pins():
    """Push AttRecord data for specific PINs to VPS"""
    return vps_push_controller.push_attrecord_for_pins()

# Legacy Attendance routes
@legacy_attendance_bp.route('/')
def legacy_attendance_dashboard():
    """Legacy attendance export dashboard"""
    return legacy_attendance_controller.dashboard()

@legacy_attendance_bp.route('/data', methods=['POST'])
def get_legacy_attendance_data():
    """Get legacy attendance data"""
    return legacy_attendance_controller.get_legacy_attendance_data()

@legacy_attendance_bp.route('/export/csv', methods=['POST'])
def export_legacy_attendance_csv():
    """Export legacy attendance data to CSV"""
    return legacy_attendance_controller.export_legacy_attendance_csv()

@legacy_attendance_bp.route('/summary', methods=['POST'])
def get_legacy_attendance_summary():
    """Get summary of legacy attendance data"""
    return legacy_attendance_controller.get_legacy_attendance_summary()
