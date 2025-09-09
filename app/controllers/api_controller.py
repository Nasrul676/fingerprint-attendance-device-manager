from flask import jsonify, request
from app.services.attendance_service import AttendanceService
from app.services.streaming_service import StreamingService
from datetime import datetime

class APIController:
    """Controller for API endpoints"""
    
    def __init__(self):
        self.attendance_service = AttendanceService()
        self.streaming_service = StreamingService()
    
    def api_attrecord_post(self):
        """Execute attrecord stored procedure"""
        try:
            data = request.get_json()
            
            if not data:
                return jsonify({
                    'status': 'error',
                    'message': 'JSON data not found'
                }), 400
            
            start_date = data.get('start_date')
            end_date = data.get('end_date')
            
            if not start_date or not end_date:
                return jsonify({
                    'status': 'error',
                    'message': 'start_date and end_date are required'
                }), 400
            
            # Validate date format
            try:
                datetime.strptime(start_date, '%Y-%m-%d')
                datetime.strptime(end_date, '%Y-%m-%d')
            except ValueError:
                return jsonify({
                    'status': 'error',
                    'message': 'Date format must be YYYY-MM-DD'
                }), 400
            
            success, message = self.attendance_service.process_stored_procedure(
                'attrecord', start_date, end_date
            )
            
            if success:
                return jsonify({
                    'status': 'success',
                    'message': f'Stored procedure attrecord executed successfully for period {start_date} to {end_date}'
                }), 200
            else:
                return jsonify({
                    'status': 'error',
                    'message': message
                }), 500
                
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'An error occurred: {str(e)}'
            }), 500
    
    def api_spjamkerja_post(self):
        """Execute spJamkerja stored procedure"""
        try:
            data = request.get_json()
            
            if not data:
                return jsonify({
                    'status': 'error',
                    'message': 'JSON data not found'
                }), 400
            
            start_date = data.get('start_date')
            end_date = data.get('end_date')
            
            if not start_date or not end_date:
                return jsonify({
                    'status': 'error',
                    'message': 'start_date and end_date are required'
                }), 400
            
            # Validate date format
            try:
                datetime.strptime(start_date, '%Y-%m-%d')
                datetime.strptime(end_date, '%Y-%m-%d')
            except ValueError:
                return jsonify({
                    'status': 'error',
                    'message': 'Date format must be YYYY-MM-DD'
                }), 400
            
            success, message = self.attendance_service.process_stored_procedure(
                'spjamkerja', start_date, end_date
            )
            
            if success:
                return jsonify({
                    'status': 'success',
                    'message': f'Stored procedure spJamkerja executed successfully for period {start_date} to {end_date}'
                }), 200
            else:
                return jsonify({
                    'status': 'error',
                    'message': message
                }), 500
                
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'An error occurred: {str(e)}'
            }), 500
    
    def api_streaming_start(self):
        """Start data streaming"""
        try:
            success, message = self.streaming_service.start_streaming()
            
            if success:
                return jsonify({
                    'status': 'success',
                    'message': message
                }), 200
            else:
                return jsonify({
                    'status': 'error',
                    'message': message
                }), 400
                
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'An error occurred: {str(e)}'
            }), 500
    
    def api_streaming_stop(self):
        """Stop data streaming"""
        try:
            success, message = self.streaming_service.stop_streaming()
            
            return jsonify({
                'status': 'success',
                'message': message
            }), 200
                
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'An error occurred: {str(e)}'
            }), 500
    
    def api_streaming_status(self):
        """Get streaming status"""
        try:
            status = self.streaming_service.get_streaming_status()
            
            return jsonify({
                'status': 'success',
                'data': status
            }), 200
                
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'An error occurred: {str(e)}'
            }), 500
    
    def api_summary(self):
        """Get attendance summary"""
        try:
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            
            if not start_date or not end_date:
                return jsonify({
                    'status': 'error',
                    'message': 'start_date and end_date are required'
                }), 400
            
            summary, error = self.attendance_service.get_fplog_summary(start_date, end_date)
            
            if error:
                return jsonify({
                    'status': 'error',
                    'message': error
                }), 500
            
            return jsonify({
                'status': 'success',
                'data': summary
            }), 200
                
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'An error occurred: {str(e)}'
            }), 500
