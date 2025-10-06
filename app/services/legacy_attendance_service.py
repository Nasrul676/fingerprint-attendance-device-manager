"""
Legacy Attendance Service
Service untuk mengambil dan mengexport data absensi legacy dengan format khusus
"""

import pandas as pd
import io
from datetime import datetime
from app.models.attendance import AttendanceModel
from config.logging_config import get_background_logger

logger = get_background_logger('LegacyAttendanceService', 'logs/legacy_attendance_service.log')

class LegacyAttendanceService:
    """Service untuk menangani data absensi legacy"""
    
    def __init__(self):
        self.attendance_model = AttendanceModel()
    
    def get_legacy_attendance_data(self, start_date, end_date):
        """
        Mengambil data absensi legacy menggunakan query khusus
        
        Args:
            start_date (str): Tanggal mulai format YYYY-MM-DD
            end_date (str): Tanggal akhir format YYYY-MM-DD
            
        Returns:
            tuple: (success, data, message)
        """
        try:
            # Format tanggal untuk query
            start_date_formatted = start_date.replace('-', '')
            end_date_formatted = end_date.replace('-', '')
            
            # Query legacy attendance data
            query = """
            SELECT * FROM (
                SELECT 
                    d.deptname,
                    e.name,
                    e.pin,
                    CONVERT(date, f.Date) AS tgl,
                    f.Date AS jam,
                    f.status,
                    f.Machine,
                    e.eid
                FROM FPLog f
                JOIN employees e ON e.pin = f.pin AND e.status = 'Active'
                JOIN departments d ON d.id = e.department
                WHERE f.Machine IN ('105','102','104','108','111','110','1','2','3','4','201','203') 
                    AND CONVERT(date, f.Date) BETWEEN ? AND ?
                
                UNION
                
                SELECT 
                    d.deptname,
                    e.name,
                    e.pin,
                    CONVERT(date, f.tgl) AS tgl,
                    f.tgl AS jam,
                    f.status,
                    f.Machine,
                    e.eid 
                FROM gagalabsens f
                JOIN employees e ON e.pin = f.pin AND e.status = 'Active'
                JOIN departments d ON d.id = e.department
                WHERE CONVERT(date, f.tgl) BETWEEN ? AND ?
            ) a
            ORDER BY pin, tgl, jam
            """
            
            logger.info(f"Executing legacy attendance query for period {start_date} to {end_date}")
            
            conn = self.attendance_model.db_manager.get_sqlserver_connection()
            if not conn:
                return False, None, "Database connection failed"
            
            cursor = conn.cursor()
            cursor.execute(query, (start_date_formatted, end_date_formatted, start_date_formatted, end_date_formatted))
            
            # Fetch all results
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            
            cursor.close()
            conn.close()
            
            # Convert to list of dictionaries
            data = []
            for row in rows:
                row_dict = {}
                for i, column in enumerate(columns):
                    value = row[i]
                    # Format datetime objects
                    if isinstance(value, datetime):
                        if column == 'tgl':
                            row_dict[column] = value.strftime('%Y-%m-%d')
                        elif column == 'jam':
                            row_dict[column] = value.strftime('%Y-%m-%d %H:%M:%S')
                        else:
                            row_dict[column] = value.strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        row_dict[column] = value
                data.append(row_dict)
            
            logger.info(f"Successfully retrieved {len(data)} legacy attendance records")
            return True, data, f"Retrieved {len(data)} records"
            
        except Exception as e:
            error_msg = f"Error retrieving legacy attendance data: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg
    
    def export_legacy_attendance_to_csv(self, start_date, end_date):
        """
        Export legacy attendance data to CSV format
        
        Args:
            start_date (str): Tanggal mulai format YYYY-MM-DD
            end_date (str): Tanggal akhir format YYYY-MM-DD
            
        Returns:
            tuple: (success, csv_data, filename, message)
        """
        try:
            # Get data
            success, data, message = self.get_legacy_attendance_data(start_date, end_date)
            
            if not success:
                return False, None, None, message
            
            if not data:
                return False, None, None, "No data found for the specified date range"
            
            # Convert to DataFrame
            df = pd.DataFrame(data)
            
            # Rename columns to more user-friendly names
            column_mapping = {
                'deptname': 'Departemen',
                'name': 'Nama Karyawan',
                'pin': 'PIN',
                'tgl': 'Tanggal',
                'jam': 'Jam',
                'status': 'Status',
                'Machine': 'Mesin',
                'eid': 'Employee ID'
            }
            
            df = df.rename(columns=column_mapping)
            
            # Reorder columns
            column_order = ['Departemen', 'Nama Karyawan', 'PIN', 'Employee ID', 'Tanggal', 'Jam', 'Status', 'Mesin']
            df = df.reindex(columns=column_order)
            
            # Create CSV in memory
            output = io.StringIO()
            df.to_csv(output, index=False, encoding='utf-8-sig')  # utf-8-sig for Excel compatibility
            
            # Convert to bytes
            csv_data = output.getvalue().encode('utf-8-sig')
            output.close()
            
            # Generate filename
            filename = f"legacy_attendance_{start_date}_to_{end_date}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            
            logger.info(f"Successfully created CSV export: {filename} with {len(data)} records")
            return True, csv_data, filename, f"CSV created successfully with {len(data)} records"
            
        except Exception as e:
            error_msg = f"Error creating CSV export: {str(e)}"
            logger.error(error_msg)
            return False, None, None, error_msg
    
    def get_legacy_attendance_summary(self, start_date, end_date):
        """
        Get summary statistics for legacy attendance data
        
        Args:
            start_date (str): Tanggal mulai format YYYY-MM-DD
            end_date (str): Tanggal akhir format YYYY-MM-DD
            
        Returns:
            tuple: (success, summary, message)
        """
        try:
            success, data, message = self.get_legacy_attendance_data(start_date, end_date)
            
            if not success:
                return False, None, message
            
            if not data:
                return True, {
                    'total_records': 0,
                    'unique_employees': 0,
                    'unique_dates': 0,
                    'departments': 0,
                    'machines': 0
                }, "No data found"
            
            df = pd.DataFrame(data)
            
            summary = {
                'total_records': len(df),
                'unique_employees': df['pin'].nunique(),
                'unique_dates': df['tgl'].nunique(),
                'departments': df['deptname'].nunique(),
                'machines': df['Machine'].nunique(),
                'date_range': {
                    'start': start_date,
                    'end': end_date
                },
                'department_breakdown': df['deptname'].value_counts().to_dict(),
                'machine_breakdown': df['Machine'].value_counts().to_dict(),
                'status_breakdown': df['status'].value_counts().to_dict()
            }
            
            return True, summary, "Summary created successfully"
            
        except Exception as e:
            error_msg = f"Error creating summary: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg

# Global service instance
legacy_attendance_service = LegacyAttendanceService()