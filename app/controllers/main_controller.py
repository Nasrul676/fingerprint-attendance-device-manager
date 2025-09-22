from flask import render_template, request, send_file
from app.services.attendance_service import AttendanceService

class MainController:
    """Controller for main web interface"""
    
    def __init__(self):
        self.attendance_service = AttendanceService()

    def export_csv(self):
        """Export attendance data to CSV"""
        start_date = request.args.get('start_date', '')
        end_date = request.args.get('end_date', '')
        
        csv_file, error = self.attendance_service.export_attendance_to_csv(
            start_date, end_date
        )
        
        if error:
            return f"Export failed: {error}", 500
        
        return send_file(
            csv_file,
            as_attachment=True,
            download_name='log_absensi.csv',
            mimetype='text/csv'
        )
