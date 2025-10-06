from flask import Flask, jsonify
from flask_toastr import Toastr
from config.config import config
from config.logging_config import disable_other_loggers
import os
import logging
from logging.handlers import RotatingFileHandler

def create_app(config_name=None):
    """Application factory pattern"""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Disable problematic loggers early to prevent conflicts
    disable_other_loggers()
    
    # Validate production configuration
    if config_name == 'production':
        try:
            config['production'].validate_config()
        except EnvironmentError as e:
            print(f"Production configuration error: {e}")
            exit(1)
    
    # Initialize Flask-Toastr
    toastr = Toastr()
    toastr.init_app(app)
    
    # Setup logging for production
    if config_name == 'production' and not app.debug:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        file_handler = RotatingFileHandler('logs/attendance_app.log', maxBytes=10240000, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('Attendance System startup')
    
    # Security headers
    @app.after_request
    def set_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        if config_name == 'production':
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        return response
    
    # Global error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        if config_name == 'production':
            return jsonify({'error': 'Resource not found'}), 404
        return jsonify({'error': 'Not found', 'message': str(error)}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        if config_name == 'production':
            app.logger.error(f'Server Error: {error}')
            return jsonify({'error': 'Internal server error'}), 500
        return jsonify({'error': 'Internal server error', 'message': str(error)}), 500
    
    # Health check endpoint
    @app.route('/health')
    def health_check():
        return jsonify({
            'status': 'healthy',
            'version': '1.0.0',
            'environment': config_name
        })
    
    # Register blueprints
    from app.routes import main_bp, api_bp, sync_bp, fplog_bp, failed_logs_bp, vps_push_bp, legacy_attendance_bp, attendance_worker_bp
    from app.controllers.attendance_report_controller import attendance_report_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(sync_bp, url_prefix='/sync')
    app.register_blueprint(fplog_bp, url_prefix='/fplog')
    app.register_blueprint(failed_logs_bp, url_prefix='/failed-logs')
    app.register_blueprint(vps_push_bp, url_prefix='/vps-push')
    app.register_blueprint(legacy_attendance_bp, url_prefix='/legacy-attendance')
    app.register_blueprint(attendance_report_bp)
    app.register_blueprint(attendance_worker_bp)  # Attendance worker dashboard
    
    return app
