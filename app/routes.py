from flask import Blueprint
from app.controllers.main_controller import MainController
from app.controllers.api_controller import APIController
from app.controllers.sync_controller import SyncController
from app.controllers.fplog_controller import FPLogController
from app.controllers.worker_controller import worker_bp

# Create blueprints
main_bp = Blueprint('main', __name__)
api_bp = Blueprint('api', __name__)
sync_bp = Blueprint('sync', __name__, url_prefix='/sync')
fplog_bp = Blueprint('fplog', __name__, url_prefix='/fplog')

# Initialize controllers
main_controller = MainController()
api_controller = APIController()
sync_controller = SyncController()
fplog_controller = FPLogController()

# Main routes
@main_bp.route('/')
def index():
    return main_controller.index()

@main_bp.route('/export')
def export_csv():
    return main_controller.export_csv()

@main_bp.route('/users')
def users():
    return main_controller.users()

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
