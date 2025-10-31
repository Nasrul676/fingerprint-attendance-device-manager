"""
spJamkerja Scheduler Controller
Handles HTTP requests for scheduler management
"""

from flask import Blueprint, jsonify, request, render_template
from app.services.spjamkerja_scheduler_service import get_spjamkerja_scheduler
from app.utils.auth_middleware import login_required
import logging

logger = logging.getLogger(__name__)

spjamkerja_scheduler_bp = Blueprint('spjamkerja_scheduler', __name__, url_prefix='/scheduler')

@spjamkerja_scheduler_bp.route('/dashboard')
@login_required
def dashboard():
    """Render scheduler dashboard page"""
    return render_template('spjamkerja_scheduler_dashboard.html')

@spjamkerja_scheduler_bp.route('/status')
@login_required
def get_scheduler_status():
    """Get scheduler status"""
    try:
        scheduler = get_spjamkerja_scheduler()
        status = scheduler.get_status()
        
        return jsonify({
            'success': True,
            'data': status
        })
    except Exception as e:
        logger.error(f"Error getting scheduler status: {e}")
        return jsonify({
            'success': False,
            'message': f"Error getting status: {str(e)}"
        }), 500

@spjamkerja_scheduler_bp.route('/start', methods=['POST'])
@login_required
def start_scheduler():
    """Start the scheduler"""
    try:
        scheduler = get_spjamkerja_scheduler()
        success, message = scheduler.start()
        
        return jsonify({
            'success': success,
            'message': message
        })
    except Exception as e:
        logger.error(f"Error starting scheduler: {e}")
        return jsonify({
            'success': False,
            'message': f"Error starting scheduler: {str(e)}"
        }), 500

@spjamkerja_scheduler_bp.route('/stop', methods=['POST'])
@login_required
def stop_scheduler():
    """Stop the scheduler"""
    try:
        scheduler = get_spjamkerja_scheduler()
        success, message = scheduler.stop()
        
        return jsonify({
            'success': success,
            'message': message
        })
    except Exception as e:
        logger.error(f"Error stopping scheduler: {e}")
        return jsonify({
            'success': False,
            'message': f"Error stopping scheduler: {str(e)}"
        }), 500

@spjamkerja_scheduler_bp.route('/force-execute', methods=['POST'])
@login_required
def force_execute():
    """Force immediate execution of spJamkerja"""
    try:
        scheduler = get_spjamkerja_scheduler()
        success, message, duration = scheduler.force_execute()
        
        return jsonify({
            'success': success,
            'message': message,
            'duration_seconds': duration
        })
    except Exception as e:
        logger.error(f"Error forcing execution: {e}")
        return jsonify({
            'success': False,
            'message': f"Error forcing execution: {str(e)}"
        }), 500

@spjamkerja_scheduler_bp.route('/set-interval', methods=['POST'])
@login_required
def set_interval():
    """Set scheduler interval"""
    try:
        data = request.get_json()
        hours = data.get('hours')
        
        if not hours:
            return jsonify({
                'success': False,
                'message': 'Hours parameter is required'
            }), 400
        
        try:
            hours = float(hours)
        except ValueError:
            return jsonify({
                'success': False,
                'message': 'Hours must be a number'
            }), 400
        
        scheduler = get_spjamkerja_scheduler()
        success, message = scheduler.set_interval(hours)
        
        return jsonify({
            'success': success,
            'message': message
        })
    except Exception as e:
        logger.error(f"Error setting interval: {e}")
        return jsonify({
            'success': False,
            'message': f"Error setting interval: {str(e)}"
        }), 500
