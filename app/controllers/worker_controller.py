"""
Controller untuk mengelola Attendance Worker
"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from app.services.attendance_worker_service import attendance_worker_service

# Create blueprint for worker management
worker_bp = Blueprint('worker', __name__)

@worker_bp.route('/worker/dashboard')
def worker_dashboard():
    """Dashboard untuk monitoring worker"""
    try:
        status = attendance_worker_service.get_worker_status()
        return render_template('worker/dashboard.html', status=status)
        
    except Exception as e:
        flash(f"Error loading worker dashboard: {str(e)}", 'error')
        return render_template('worker/dashboard.html', status={'error': str(e)})

@worker_bp.route('/worker/start', methods=['POST'])
def start_worker():
    """Memulai worker"""
    try:
        success, message = attendance_worker_service.start_worker()
        
        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'message': message}), 400
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@worker_bp.route('/worker/stop', methods=['POST'])
def stop_worker():
    """Menghentikan worker"""
    try:
        success, message = attendance_worker_service.stop_worker()
        
        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'message': message}), 400
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@worker_bp.route('/worker/status')
def get_worker_status():
    """API untuk mendapatkan status worker"""
    try:
        status = attendance_worker_service.get_worker_status()
        return jsonify({'success': True, 'data': status})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@worker_bp.route('/worker/run-now', methods=['POST'])
def run_worker_now():
    """Paksa menjalankan worker sekarang"""
    try:
        success, message = attendance_worker_service.force_run_now()
        
        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'message': message}), 400
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# Helper function to register blueprint
def register_worker_blueprint(app):
    """Register worker blueprint dengan app"""
    app.register_blueprint(worker_bp, url_prefix='/api')
    return worker_bp
