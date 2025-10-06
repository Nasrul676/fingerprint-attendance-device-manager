"""
Legacy Attendance Controller
Controller untuk menangani API requests terkait export data absensi legacy
"""

from flask import request, jsonify, Response, render_template
from datetime import datetime
from app.services.legacy_attendance_service import legacy_attendance_service
from config.logging_config import get_background_logger

logger = get_background_logger('LegacyAttendanceController', 'logs/legacy_attendance_controller.log')

class LegacyAttendanceController:
    """Controller untuk legacy attendance operations"""
    
    def __init__(self):
        self.legacy_service = legacy_attendance_service
    
    def dashboard(self):
        """Legacy attendance export dashboard"""
        try:
            return render_template('legacy_attendance_export.html')
        except Exception as e:
            logger.error(f"Error rendering legacy attendance dashboard: {e}")
            return jsonify({
                'success': False,
                'message': f'Dashboard error: {str(e)}'
            }), 500
    
    def get_legacy_attendance_data(self):
        """Get legacy attendance data"""
        try:
            data = request.get_json() or {}
            start_date = data.get('start_date')
            end_date = data.get('end_date')
            
            # Validate required parameters
            if not start_date or not end_date:
                return jsonify({
                    'success': False,
                    'message': 'start_date and end_date are required'
                }), 400
            
            # Validate date format
            try:
                datetime.strptime(start_date, '%Y-%m-%d')
                datetime.strptime(end_date, '%Y-%m-%d')
            except ValueError:
                return jsonify({
                    'success': False,
                    'message': 'Invalid date format. Use YYYY-MM-DD'
                }), 400
            
            logger.info(f"Getting legacy attendance data for period {start_date} to {end_date}")
            
            # Get data
            success, data, message = self.legacy_service.get_legacy_attendance_data(start_date, end_date)
            
            if success:
                return jsonify({
                    'success': True,
                    'data': data,
                    'record_count': len(data) if data else 0,
                    'start_date': start_date,
                    'end_date': end_date,
                    'message': message,
                    'timestamp': datetime.now().isoformat()
                })
            else:
                return jsonify({
                    'success': False,
                    'message': message,
                    'start_date': start_date,
                    'end_date': end_date
                }), 500
        
        except Exception as e:
            logger.error(f"Error in get_legacy_attendance_data: {e}")
            return jsonify({
                'success': False,
                'message': f'Internal error: {str(e)}'
            }), 500
    
    def export_legacy_attendance_csv(self):
        """Export legacy attendance data to CSV"""
        try:
            data = request.get_json() or {}
            start_date = data.get('start_date')
            end_date = data.get('end_date')
            
            # Validate required parameters
            if not start_date or not end_date:
                return jsonify({
                    'success': False,
                    'message': 'start_date and end_date are required'
                }), 400
            
            # Validate date format
            try:
                datetime.strptime(start_date, '%Y-%m-%d')
                datetime.strptime(end_date, '%Y-%m-%d')
            except ValueError:
                return jsonify({
                    'success': False,
                    'message': 'Invalid date format. Use YYYY-MM-DD'
                }), 400
            
            logger.info(f"Exporting legacy attendance CSV for period {start_date} to {end_date}")
            
            # Export to CSV
            success, csv_data, filename, message = self.legacy_service.export_legacy_attendance_to_csv(start_date, end_date)
            
            if success:
                # Return CSV file as download
                response = Response(
                    csv_data,
                    mimetype='text/csv',
                    headers={
                        'Content-Disposition': f'attachment; filename="{filename}"',
                        'Content-Type': 'text/csv; charset=utf-8'
                    }
                )
                
                logger.info(f"Successfully exported CSV: {filename}")
                return response
            else:
                return jsonify({
                    'success': False,
                    'message': message,
                    'start_date': start_date,
                    'end_date': end_date
                }), 500
        
        except Exception as e:
            logger.error(f"Error in export_legacy_attendance_csv: {e}")
            return jsonify({
                'success': False,
                'message': f'Internal error: {str(e)}'
            }), 500
    
    def get_legacy_attendance_summary(self):
        """Get summary of legacy attendance data"""
        try:
            data = request.get_json() or {}
            start_date = data.get('start_date')
            end_date = data.get('end_date')
            
            # Validate required parameters
            if not start_date or not end_date:
                return jsonify({
                    'success': False,
                    'message': 'start_date and end_date are required'
                }), 400
            
            # Validate date format
            try:
                datetime.strptime(start_date, '%Y-%m-%d')
                datetime.strptime(end_date, '%Y-%m-%d')
            except ValueError:
                return jsonify({
                    'success': False,
                    'message': 'Invalid date format. Use YYYY-MM-DD'
                }), 400
            
            logger.info(f"Getting legacy attendance summary for period {start_date} to {end_date}")
            
            # Get summary
            success, summary, message = self.legacy_service.get_legacy_attendance_summary(start_date, end_date)
            
            if success:
                return jsonify({
                    'success': True,
                    'summary': summary,
                    'start_date': start_date,
                    'end_date': end_date,
                    'message': message,
                    'timestamp': datetime.now().isoformat()
                })
            else:
                return jsonify({
                    'success': False,
                    'message': message,
                    'start_date': start_date,
                    'end_date': end_date
                }), 500
        
        except Exception as e:
            logger.error(f"Error in get_legacy_attendance_summary: {e}")
            return jsonify({
                'success': False,
                'message': f'Internal error: {str(e)}'
            }), 500

# Global controller instance
legacy_attendance_controller = LegacyAttendanceController()