"""
Controller untuk mengelola data absensi yang gagal (gagalabsens)
"""
from flask import render_template, request, jsonify
from app.models.attendance import AttendanceModel

class FailedLogController:
    """Controller untuk menampilkan dan mengelola data absensi yang gagal"""
    
    def __init__(self):
        self.attendance_model = AttendanceModel()
    
    def failed_logs_dashboard(self):
        """Menampilkan dashboard untuk data absensi yang gagal"""
        try:
            # Get pagination parameters
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 50, type=int)
            start_date = request.args.get('start_date', '')
            end_date = request.args.get('end_date', '')
            
            # Limit per_page to prevent excessive load
            per_page = min(per_page, 100)
            
            # Get failed attendance logs
            logs, total, total_pages = self.attendance_model.get_failed_attendance_logs(
                start_date if start_date else None,
                end_date if end_date else None,
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