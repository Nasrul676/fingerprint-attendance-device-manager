from flask import render_template, request, send_file
from app.services.attendance_service import AttendanceService

class MainController:
    """Controller for main web interface"""
    
    def __init__(self):
        self.attendance_service = AttendanceService()
    
    def index(self):
        """Main page: display attendance data with pagination and date filtering"""
        page = request.args.get('page', 1, type=int)
        per_page = 20
        start_date = request.args.get('start_date', '')
        end_date = request.args.get('end_date', '')
        
        logs, total, total_pages = self.attendance_service.get_attendance_data(
            start_date, end_date, page, per_page
        )
        
        return render_template(
            'index.html', 
            logs=logs, 
            page=page, 
            total_pages=total_pages, 
            start_date=start_date, 
            end_date=end_date,
            total=total
        )
    
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
    
    def users(self):
        """Display users from fingerprint device"""
        # This would need to be implemented based on device service
        user_list = []  # Placeholder
        return render_template('users.html', users=user_list)
