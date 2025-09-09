from app.models.attendance import AttendanceModel
import pandas as pd
import io

class AttendanceService:
    """Service layer for attendance business logic"""
    
    def __init__(self):
        self.attendance_model = AttendanceModel()
    
    def get_attendance_data(self, start_date=None, end_date=None, page=1, per_page=20):
        """Get attendance data with business logic applied"""
        logs, total, total_pages = self.attendance_model.get_attendance_logs(
            start_date, end_date, page, per_page
        )
        
        # Apply any business logic here
        # For example, format timestamps, calculate durations, etc.
        processed_logs = []
        for log in logs:
            processed_log = log.copy()
            # Add any calculated fields or formatting
            processed_logs.append(processed_log)
        
        return processed_logs, total, total_pages
    
    def export_attendance_to_csv(self, start_date=None, end_date=None):
        """Export attendance data to CSV format"""
        try:
            # Get all data (no pagination for export)
            logs, _, _ = self.attendance_model.get_attendance_logs(
                start_date, end_date, page=1, per_page=10000
            )
            
            # Convert to DataFrame
            df = pd.DataFrame(logs)
            
            # Create CSV in memory
            proxy = io.StringIO()
            df.to_csv(proxy, index=False)
            
            # Convert to bytes
            mem = io.BytesIO()
            mem.write(proxy.getvalue().encode('utf-8'))
            mem.seek(0)
            proxy.close()
            
            return mem, None
            
        except Exception as e:
            return None, f"Export failed: {str(e)}"
    
    def process_stored_procedure(self, procedure_name, start_date, end_date):
        """Process stored procedure execution"""
        try:
            if procedure_name == 'attrecord':
                success, message = self.attendance_model.execute_attrecord_procedure(
                    start_date, end_date
                )
            elif procedure_name == 'spjamkerja':
                success, message = self.attendance_model.execute_spjamkerja_procedure(
                    start_date, end_date
                )
            else:
                return False, "Unknown procedure"
            
            return success, message
            
        except Exception as e:
            return False, f"Service error: {str(e)}"
    
    def get_fplog_summary(self, start_date, end_date):
        """Get summary of FPLog data"""
        try:
            data, total, _ = self.attendance_model.get_fplog_data(
                start_date, end_date, page=1, per_page=10000
            )
            
            # Calculate summary statistics
            summary = {
                'total_records': total,
                'date_range': {
                    'start': start_date,
                    'end': end_date
                },
                'machines': {},
                'status_counts': {}
            }
            
            # Count by machine and status
            for record in data:
                machine = record.get('Machine', 'Unknown')
                status = record.get('Status', 'Unknown')
                
                if machine not in summary['machines']:
                    summary['machines'][machine] = 0
                summary['machines'][machine] += 1
                
                if status not in summary['status_counts']:
                    summary['status_counts'][status] = 0
                summary['status_counts'][status] += 1
            
            return summary, None
            
        except Exception as e:
            return None, f"Summary calculation failed: {str(e)}"
