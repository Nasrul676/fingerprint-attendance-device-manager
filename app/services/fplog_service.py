"""
Service for handling FPLog data operations
"""
from datetime import datetime, timedelta
import pandas as pd
from io import BytesIO
from app.models.attendance import AttendanceModel
from config.database import db_manager

class FPLogService:
    """Service for FPLog data operations including search, filter, and export"""
    
    def __init__(self):
        self.attendance_model = AttendanceModel()
        self.db_manager = db_manager
        
    def _determine_status_display(self, status, device_name):
        """Convert status code to display text based on device rules"""
        if device_name == '104':
            if status == 'I':
                return 'Masuk'
            elif status == 'O':
                return 'Keluar'
            elif status == 'i':
                return 'Masuk Istirahat'
            elif status == 'o':
                return 'Keluar Istirahat'
            else:
                return str(status)
        elif device_name == '102':
            if status == 0 or status == '0':
                return 'Masuk'
            elif status == 1 or status == '1':
                return 'Keluar'
            else:
                return str(status)
        else:
            # Standard mapping for other devices
            status_map = {
                0: 'Check In',
                1: 'Check Out', 
                2: 'Break Out',
                3: 'Break In',
                4: 'OT In',
                5: 'OT Out',
                'i': 'Masuk Istirahat',
                'o': 'Keluar Istirahat'
            }
            return status_map.get(int(status) if str(status).isdigit() else status, str(status))
    
    def search_fplog_data(self, filters=None):
        """Search FPLog data with filters"""
        try:
            conn = self.db_manager.get_sqlserver_connection()
            if not conn:
                return False, "Tidak dapat terhubung ke database", []
            
            cursor = conn.cursor()
            
            # Base query
            base_query = """
                SELECT PIN, Date, Machine, Status, fpid
                FROM FPLog 
                WHERE 1=1
            """
            
            params = []
            conditions = []
            
            # Apply filters
            if filters:
                if filters.get('pin'):
                    conditions.append("PIN LIKE ?")
                    params.append(f"%{filters['pin']}%")
                
                if filters.get('machine'):
                    conditions.append("Machine = ?")
                    params.append(filters['machine'])
                
                if filters.get('start_date'):
                    conditions.append("CAST(Date AS DATE) >= ?")
                    params.append(filters['start_date'])
                
                if filters.get('end_date'):
                    conditions.append("CAST(Date AS DATE) <= ?")
                    params.append(filters['end_date'])
                
                # Note: status filtering is done after query since we need to apply device-specific logic
            
            # Add conditions to query
            if conditions:
                base_query += " AND " + " AND ".join(conditions)
            
            # Add ordering
            base_query += " ORDER BY Date DESC"
            
            # Add limit if specified
            if filters and filters.get('limit'):
                base_query += f" OFFSET 0 ROWS FETCH NEXT {int(filters['limit'])} ROWS ONLY"
            
            cursor.execute(base_query, tuple(params))
            rows = cursor.fetchall()
            
            # Convert to dictionary manually
            columns = [column[0] for column in cursor.description]
            raw_data = [dict(zip(columns, row)) for row in rows]
            
            # Process data to add display status and format dates
            processed_data = []
            for row in raw_data:
                row_copy = dict(row)
                row_copy['status_display'] = self._determine_status_display(row['Status'], row['Machine'])
                
                # Format dates in Python instead of SQL
                if row['Date']:
                    row_copy['date_only'] = row['Date'].strftime('%Y-%m-%d')
                    row_copy['time_only'] = row['Date'].strftime('%H:%M:%S')
                else:
                    row_copy['date_only'] = ''
                    row_copy['time_only'] = ''
                
                # Apply status filter after processing if specified
                if filters.get('status') and filters['status'] != 'all':
                    if row_copy['status_display'] != filters['status']:
                        continue
                        
                processed_data.append(row_copy)
            
            cursor.close()
            conn.close()
            
            return True, "Data berhasil diambil", processed_data
            
        except Exception as e:
            return False, f"Error mengambil data: {str(e)}", []
    
    def get_machine_list(self):
        """Get list of unique machines from FPLog"""
        try:
            conn = self.db_manager.get_sqlserver_connection()
            if not conn:
                return []
            
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT Machine FROM FPLog ORDER BY Machine")
            machines = [row[0] for row in cursor.fetchall()]
            
            cursor.close()
            conn.close()
            
            return machines
            
        except Exception as e:
            print(f"Error getting machine list: {e}")
            return []
    
    def get_status_list(self):
        """Get list of unique status values from FPLog"""
        try:
            conn = self.db_manager.get_sqlserver_connection()
            if not conn:
                return []
            
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT Status FROM FPLog ORDER BY Status")
            statuses = [row[0] for row in cursor.fetchall()]
            
            cursor.close()
            conn.close()
            
            return statuses
            
        except Exception as e:
            print(f"Error getting status list: {e}")
            return []
    
    def export_to_excel(self, data, filters=None):
        """Export FPLog data to Excel format"""
        try:
            if not data:
                return None, "Tidak ada data untuk diekspor"
            
            # Prepare data for DataFrame
            excel_data = []
            for row in data:
                excel_data.append({
                    'PIN': row['PIN'],
                    'Tanggal': row['date_only'],
                    'Waktu': row['time_only'],
                    'Mesin': row['Machine'],
                    'Status Kode': row['Status'],
                    'Status': row['status_display'],
                    'FPID': row['fpid']
                })
            
            # Create DataFrame
            df = pd.DataFrame(excel_data)
            
            # Create Excel file in memory
            output = BytesIO()
            
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                # Write main data
                df.to_excel(writer, sheet_name='Data Absensi', index=False)
                
                # Add summary sheet
                summary_data = self._create_summary(data)
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name='Ringkasan', index=False)
                
                # Format the Excel file
                workbook = writer.book
                worksheet = writer.sheets['Data Absensi']
                
                # Auto-adjust column width
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
            
            output.seek(0)
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"data_absensi_{timestamp}.xlsx"
            
            return output.getvalue(), filename
            
        except Exception as e:
            return None, f"Error membuat file Excel: {str(e)}"
    
    def _create_summary(self, data):
        """Create summary data for Excel export"""
        summary = []
        
        # Count by machine
        machine_counts = {}
        status_counts = {}
        date_counts = {}
        
        for row in data:
            machine = row['Machine']
            status = row['status_display']
            date = row['date_only']
            
            machine_counts[machine] = machine_counts.get(machine, 0) + 1
            status_counts[status] = status_counts.get(status, 0) + 1
            date_counts[date] = date_counts.get(date, 0) + 1
        
        # Machine summary
        summary.append({'Kategori': 'Total Record', 'Item': 'Semua Data', 'Jumlah': len(data)})
        summary.append({'Kategori': '', 'Item': '', 'Jumlah': ''})
        
        summary.append({'Kategori': 'Per Mesin', 'Item': '', 'Jumlah': ''})
        for machine, count in sorted(machine_counts.items()):
            summary.append({'Kategori': '', 'Item': f'Mesin {machine}', 'Jumlah': count})
        
        summary.append({'Kategori': '', 'Item': '', 'Jumlah': ''})
        summary.append({'Kategori': 'Per Status', 'Item': '', 'Jumlah': ''})
        for status, count in sorted(status_counts.items()):
            summary.append({'Kategori': '', 'Item': status, 'Jumlah': count})
        
        return summary
    
    def get_fplog_statistics(self):
        """Get FPLog statistics for dashboard"""
        try:
            conn = self.db_manager.get_sqlserver_connection()
            if not conn:
                return {}
            
            cursor = conn.cursor(dictionary=True)
            
            stats = {}
            
            # Total records
            cursor.execute("SELECT COUNT(*) as total FROM FPLog")
            stats['total_records'] = cursor.fetchone()['total']
            
            # Records today
            cursor.execute("SELECT COUNT(*) as today FROM FPLog WHERE DATE(Date) = CURDATE()")
            stats['today_records'] = cursor.fetchone()['today']
            
            # Records this week
            cursor.execute("SELECT COUNT(*) as week FROM FPLog WHERE YEARWEEK(Date) = YEARWEEK(NOW())")
            stats['week_records'] = cursor.fetchone()['week']
            
            # Records this month
            cursor.execute("SELECT COUNT(*) as month FROM FPLog WHERE YEAR(Date) = YEAR(NOW()) AND MONTH(Date) = MONTH(NOW())")
            stats['month_records'] = cursor.fetchone()['month']
            
            # Latest record
            cursor.execute("SELECT Date FROM FPLog ORDER BY Date DESC LIMIT 1")
            latest = cursor.fetchone()
            stats['latest_record'] = latest['Date'] if latest else None
            
            cursor.close()
            conn.close()
            
            return stats
            
        except Exception as e:
            print(f"Error getting FPLog statistics: {e}")
            return {}
    
    def get_machine_list(self):
        """Get list of unique machines from FPLog"""
        try:
            conn = self.db_manager.get_sqlserver_connection()
            if not conn:
                return []
            
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT Machine FROM FPLog ORDER BY Machine")
            machines = [row[0] for row in cursor.fetchall()]
            
            cursor.close()
            conn.close()
            
            return machines
            
        except Exception as e:
            print(f"Error getting machine list: {e}")
            return []
    
    def get_status_list(self):
        """Get list of possible status values"""
        return ['Masuk', 'Keluar', 'Break Masuk', 'Break Keluar', 'Lembur Masuk', 'Lembur Keluar', 'Masuk Istirahat', 'Keluar Istirahat']
