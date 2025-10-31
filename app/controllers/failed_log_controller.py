"""
Controller untuk mengelola data absensi yang gagal (gagalabsens)
"""
from flask import render_template, request, jsonify
from werkzeug.utils import secure_filename
import os
import tempfile
from app.models.attendance import AttendanceModel
from app.services.failed_attendance_upload_service import failed_attendance_upload_service

class FailedLogController:
    """Controller untuk menampilkan dan mengelola data absensi yang gagal"""
    
    def __init__(self):
        self.attendance_model = AttendanceModel()
        self.upload_service = failed_attendance_upload_service
        
        # Allowed file extensions
        self.ALLOWED_EXTENSIONS = {'xlsx', 'xls'}
    
    def _allowed_file(self, filename):
        """Check if file extension is allowed"""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in self.ALLOWED_EXTENSIONS
    
    def failed_logs_dashboard(self):
        """Menampilkan dashboard untuk data absensi yang gagal"""
        try:
            # Get pagination parameters
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 50, type=int)
            start_date = request.args.get('start_date', '')
            end_date = request.args.get('end_date', '')
            pin_filter = request.args.get('pin_filter', '')
            
            # Limit per_page to prevent excessive load
            per_page = min(per_page, 100)
            
            # Get failed attendance logs
            logs, total, total_pages = self.attendance_model.get_failed_attendance_logs(
                start_date if start_date else None,
                end_date if end_date else None,
                pin_filter if pin_filter else None,
                page,
                per_page
            )
            
            # Get statistics
            stats = self.attendance_model.get_failed_attendance_stats()
            
            return render_template(
                'failed_logs.html',
                logs=logs,
                total=total,
                page=page,
                total_pages=total_pages,
                per_page=per_page,
                start_date=start_date,
                end_date=end_date,
                pin_filter=pin_filter,
                stats=stats
            )
            
        except Exception as e:
            print(f"Error in failed_logs_dashboard: {e}")
            return render_template(
                'failed_logs.html',
                logs=[],
                total=0,
                page=1,
                total_pages=0,
                per_page=50,
                start_date='',
                end_date='',
                stats={},
                error=str(e)
            )
    
    def get_failed_logs_stats(self):
        """API endpoint untuk mendapatkan statistik data gagal absen"""
        try:
            stats = self.attendance_model.get_failed_attendance_stats()
            return jsonify({
                'success': True,
                'data': stats
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    def search_failed_logs(self):
        """Mencari data absensi yang gagal berdasarkan filter"""
        try:
            # Get search parameters
            page = request.form.get('page', 1, type=int)
            per_page = request.form.get('per_page', 50, type=int)
            start_date = request.form.get('start_date', '')
            end_date = request.form.get('end_date', '')
            
            # Limit per_page to prevent excessive load
            per_page = min(per_page, 100)
            
            # Get filtered data
            logs, total, total_pages = self.attendance_model.get_failed_attendance_logs(
                start_date if start_date else None,
                end_date if end_date else None,
                page,
                per_page
            )
            
            return jsonify({
                'success': True,
                'data': {
                    'logs': logs,
                    'total': total,
                    'page': page,
                    'total_pages': total_pages,
                    'per_page': per_page
                }
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    def upload_excel_file(self):
        """Upload dan proses file Excel gagal absensi"""
        try:
            # Check if file is present
            if 'excel_file' not in request.files:
                return jsonify({
                    'success': False,
                    'message': 'No file selected'
                }), 400
            
            file = request.files['excel_file']
            
            # Check if file is selected
            if file.filename == '':
                return jsonify({
                    'success': False,
                    'message': 'No file selected'
                }), 400
            
            # Check file extension
            if not self._allowed_file(file.filename):
                return jsonify({
                    'success': False,
                    'message': 'File type not allowed. Please upload Excel file (.xlsx or .xls)'
                }), 400
            
            # Save file temporarily
            filename = secure_filename(file.filename)
            temp_dir = tempfile.gettempdir()
            temp_path = os.path.join(temp_dir, f"upload_{filename}")
            
            file.save(temp_path)
            
            # Process the Excel file
            success, message, stats = self.upload_service.process_excel_upload(temp_path)
            
            if success:
                return jsonify({
                    'success': True,
                    'message': message,
                    'statistics': stats
                })
            else:
                return jsonify({
                    'success': False,
                    'message': message,
                    'statistics': stats
                }), 400
                
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'Upload error: {str(e)}'
            }), 500
    
    def validate_excel_template(self):
        """Validate Excel file structure without processing"""
        try:
            if 'excel_file' not in request.files:
                return jsonify({
                    'success': False,
                    'message': 'No file selected'
                }), 400
            
            file = request.files['excel_file']
            
            if file.filename == '':
                return jsonify({
                    'success': False,
                    'message': 'No file selected'
                }), 400
            
            if not self._allowed_file(file.filename):
                return jsonify({
                    'success': False,
                    'message': 'File type not allowed. Please upload Excel file (.xlsx or .xls)'
                }), 400
            
            # Save file temporarily for validation
            filename = secure_filename(file.filename)
            temp_dir = tempfile.gettempdir()
            temp_path = os.path.join(temp_dir, f"validate_{filename}")
            
            file.save(temp_path)
            
            # Validate file structure
            success, message, missing_columns = self.upload_service.validate_excel_template(temp_path)
            
            # Cleanup temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
            
            return jsonify({
                'success': success,
                'message': message,
                'missing_columns': missing_columns
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'Validation error: {str(e)}'
            }), 500