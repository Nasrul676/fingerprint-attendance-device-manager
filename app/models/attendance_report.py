from config.database import db_manager
from datetime import datetime, date
import pandas as pd
from io import BytesIO

class AttendanceReportModel:
    """Model for handling attendance report data with filtering and export capabilities"""
    
    def __init__(self):
        self.db_manager = db_manager
    
    def get_attendance_data(self, filters=None, page=1, per_page=50, sort_by='tgl', sort_order='DESC'):
        """
        Get attendance data with filtering and pagination
        
        Args:
            filters (dict): Dictionary containing filter criteria
            page (int): Page number for pagination
            per_page (int): Number of records per page
            sort_by (str): Column to sort by
            sort_order (str): ASC or DESC
        
        Returns:
            tuple: (data_list, total_count, total_pages)
        """
        try:
            conn = self.db_manager.get_sqlserver_connection()
            if not conn:
                return [], 0, 0
            
            cursor = conn.cursor()
            
            # Build WHERE clause based on filters
            where_conditions = []
            params = []
            
            if filters:
                if filters.get('start_date'):
                    where_conditions.append("tgl >= ?")
                    params.append(filters['start_date'])
                
                if filters.get('end_date'):
                    where_conditions.append("tgl <= ?")
                    params.append(filters['end_date'])
                
                if filters.get('pin'):
                    where_conditions.append("pin LIKE ?")
                    params.append(f"%{filters['pin']}%")
                
                if filters.get('name'):
                    where_conditions.append("name LIKE ?")
                    params.append(f"%{filters['name']}%")
                
                if filters.get('jabatan'):
                    where_conditions.append("jabatan LIKE ?")
                    params.append(f"%{filters['jabatan']}%")
                
                if filters.get('lokasi'):
                    where_conditions.append("lokasi LIKE ?")
                    params.append(f"%{filters['lokasi']}%")
                
                if filters.get('deptname'):
                    where_conditions.append("deptname LIKE ?")
                    params.append(f"%{filters['deptname']}%")
                
                if filters.get('shift'):
                    where_conditions.append("shift LIKE ?")
                    params.append(f"%{filters['shift']}%")
                
                if filters.get('keterangan'):
                    where_conditions.append("keterangan LIKE ?")
                    params.append(f"%{filters['keterangan']}%")
            
            where_clause = ""
            if where_conditions:
                where_clause = "WHERE " + " AND ".join(where_conditions)
            
            # Get total count
            count_query = f"""
                SELECT COUNT(*) as total
                FROM attrecords
                {where_clause}
            """
            
            cursor.execute(count_query, params)
            total_count = cursor.fetchone()[0]
            total_pages = (total_count + per_page - 1) // per_page
            
            # Get paginated data
            offset = (page - 1) * per_page
            
            # Validate sort_by to prevent SQL injection
            valid_columns = [
                'id', 'tgl', 'fpid', 'pin', 'name', 'jabatan', 'lokasi', 
                'deptname', 'masuk', 'keluar', 'shift', 'created_at', 
                'updated_at', 'keterangan', 'masuk_produksi', 'keluar_produksi'
            ]
            
            if sort_by not in valid_columns:
                sort_by = 'tgl'
            
            if sort_order.upper() not in ['ASC', 'DESC']:
                sort_order = 'DESC'
            
            data_query = f"""
                SELECT 
                    id, tgl, fpid, pin, name, jabatan, lokasi, deptname,
                    masuk, keluar, shift, created_at, updated_at, keterangan,
                    masuk_produksi, keluar_produksi
                FROM attrecords
                {where_clause}
                ORDER BY {sort_by} {sort_order}
                OFFSET ? ROWS
                FETCH NEXT ? ROWS ONLY
            """
            
            cursor.execute(data_query, params + [offset, per_page])
            rows = cursor.fetchall()
            
            # Convert to list of dictionaries
            columns = [
                'id', 'tgl', 'fpid', 'pin', 'name', 'jabatan', 'lokasi', 'deptname',
                'masuk', 'keluar', 'shift', 'created_at', 'updated_at', 'keterangan',
                'masuk_produksi', 'keluar_produksi'
            ]
            
            data_list = []
            for row in rows:
                record = {}
                for i, column in enumerate(columns):
                    value = row[i]
                    # Format datetime and time fields
                    if column in ['created_at', 'updated_at'] and value:
                        record[column] = value.strftime('%Y-%m-%d %H:%M:%S') if isinstance(value, datetime) else str(value)
                    elif column == 'tgl' and value:
                        record[column] = value.strftime('%Y-%m-%d') if isinstance(value, date) else str(value)
                    elif column in ['masuk', 'keluar', 'masuk_produksi', 'keluar_produksi'] and value:
                        # Handle time fields
                        if hasattr(value, 'strftime'):
                            record[column] = value.strftime('%H:%M:%S')
                        else:
                            record[column] = str(value)
                    else:
                        record[column] = value
                
                data_list.append(record)
            
            cursor.close()
            conn.close()
            
            return data_list, total_count, total_pages
            
        except Exception as e:
            print(f"Error getting attendance data: {e}")
            return [], 0, 0
    
    def export_to_excel(self, filters=None):
        """
        Export attendance data to Excel format
        
        Args:
            filters (dict): Dictionary containing filter criteria
        
        Returns:
            BytesIO: Excel file as bytes
        """
        try:
            conn = self.db_manager.get_sqlserver_connection()
            if not conn:
                return None
            
            cursor = conn.cursor()
            
            # Build WHERE clause based on filters
            where_conditions = []
            params = []
            
            if filters:
                if filters.get('start_date'):
                    where_conditions.append("tgl >= ?")
                    params.append(filters['start_date'])
                
                if filters.get('end_date'):
                    where_conditions.append("tgl <= ?")
                    params.append(filters['end_date'])
                
                if filters.get('pin'):
                    where_conditions.append("pin LIKE ?")
                    params.append(f"%{filters['pin']}%")
                
                if filters.get('name'):
                    where_conditions.append("name LIKE ?")
                    params.append(f"%{filters['name']}%")
                
                if filters.get('jabatan'):
                    where_conditions.append("jabatan LIKE ?")
                    params.append(f"%{filters['jabatan']}%")
                
                if filters.get('lokasi'):
                    where_conditions.append("lokasi LIKE ?")
                    params.append(f"%{filters['lokasi']}%")
                
                if filters.get('deptname'):
                    where_conditions.append("deptname LIKE ?")
                    params.append(f"%{filters['deptname']}%")
                
                if filters.get('shift'):
                    where_conditions.append("shift LIKE ?")
                    params.append(f"%{filters['shift']}%")
                
                if filters.get('keterangan'):
                    where_conditions.append("keterangan LIKE ?")
                    params.append(f"%{filters['keterangan']}%")
            
            where_clause = ""
            if where_conditions:
                where_clause = "WHERE " + " AND ".join(where_conditions)
            
            # Get all data for export
            query = f"""
                SELECT 
                    id as ID,
                    tgl as Tanggal,
                    fpid as FPID,
                    pin as PIN,
                    name as Nama,
                    jabatan as Jabatan,
                    lokasi as Lokasi,
                    deptname as Departemen,
                    masuk as 'Jam Masuk',
                    keluar as 'Jam Keluar',
                    shift as Shift,
                    created_at as 'Dibuat Pada',
                    updated_at as 'Diupdate Pada',
                    keterangan as Keterangan,
                    masuk_produksi as 'Masuk Produksi',
                    keluar_produksi as 'Keluar Produksi'
                FROM attrecords
                {where_clause}
                ORDER BY tgl DESC, pin ASC
            """
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            # Get column names
            columns = [column[0] for column in cursor.description]
            
            cursor.close()
            conn.close()
            
            # Create DataFrame
            df = pd.DataFrame.from_records(rows, columns=columns)
            
            # Create Excel file in memory
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Data Absensi', index=False)
                
                # Get the workbook and worksheet
                workbook = writer.book
                worksheet = writer.sheets['Data Absensi']
                
                # Auto-adjust column widths
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
            return output
            
        except Exception as e:
            print(f"Error exporting to Excel: {e}")
            return None
    
    def get_filter_options(self):
        """
        Get unique values for filter dropdowns
        
        Returns:
            dict: Dictionary containing lists of unique values for each filter field
        """
        try:
            conn = self.db_manager.get_sqlserver_connection()
            if not conn:
                return {}
            
            cursor = conn.cursor()
            
            filter_options = {}
            
            # Get unique jabatan values
            cursor.execute("SELECT DISTINCT jabatan FROM attrecords WHERE jabatan IS NOT NULL ORDER BY jabatan")
            filter_options['jabatan'] = [row[0] for row in cursor.fetchall()]
            
            # Get unique lokasi values
            cursor.execute("SELECT DISTINCT lokasi FROM attrecords WHERE lokasi IS NOT NULL ORDER BY lokasi")
            filter_options['lokasi'] = [row[0] for row in cursor.fetchall()]
            
            # Get unique deptname values
            cursor.execute("SELECT DISTINCT deptname FROM attrecords WHERE deptname IS NOT NULL ORDER BY deptname")
            filter_options['deptname'] = [row[0] for row in cursor.fetchall()]
            
            # Get unique shift values
            cursor.execute("SELECT DISTINCT shift FROM attrecords WHERE shift IS NOT NULL ORDER BY shift")
            filter_options['shift'] = [row[0] for row in cursor.fetchall()]
            
            # Get unique keterangan values
            cursor.execute("SELECT DISTINCT keterangan FROM attrecords WHERE keterangan IS NOT NULL ORDER BY keterangan")
            filter_options['keterangan'] = [row[0] for row in cursor.fetchall()]
            
            cursor.close()
            conn.close()
            
            return filter_options
            
        except Exception as e:
            print(f"Error getting filter options: {e}")
            return {}
    
    def get_summary_stats(self, filters=None):
        """
        Get summary statistics for the attendance data
        
        Args:
            filters (dict): Dictionary containing filter criteria
        
        Returns:
            dict: Summary statistics
        """
        try:
            conn = self.db_manager.get_sqlserver_connection()
            if not conn:
                return {}
            
            cursor = conn.cursor()
            
            # Build WHERE clause based on filters
            where_conditions = []
            params = []
            
            if filters:
                if filters.get('start_date'):
                    where_conditions.append("tgl >= ?")
                    params.append(filters['start_date'])
                
                if filters.get('end_date'):
                    where_conditions.append("tgl <= ?")
                    params.append(filters['end_date'])
                
                if filters.get('pin'):
                    where_conditions.append("pin LIKE ?")
                    params.append(f"%{filters['pin']}%")
                
                if filters.get('name'):
                    where_conditions.append("name LIKE ?")
                    params.append(f"%{filters['name']}%")
                
                if filters.get('jabatan'):
                    where_conditions.append("jabatan LIKE ?")
                    params.append(f"%{filters['jabatan']}%")
                
                if filters.get('lokasi'):
                    where_conditions.append("lokasi LIKE ?")
                    params.append(f"%{filters['lokasi']}%")
                
                if filters.get('deptname'):
                    where_conditions.append("deptname LIKE ?")
                    params.append(f"%{filters['deptname']}%")
                
                if filters.get('shift'):
                    where_conditions.append("shift LIKE ?")
                    params.append(f"%{filters['shift']}%")
                
                if filters.get('keterangan'):
                    where_conditions.append("keterangan LIKE ?")
                    params.append(f"%{filters['keterangan']}%")
            
            where_clause = ""
            if where_conditions:
                where_clause = "WHERE " + " AND ".join(where_conditions)
            
            # Get summary statistics
            summary_query = f"""
                SELECT 
                    COUNT(*) as total_records,
                    COUNT(DISTINCT pin) as unique_employees,
                    COUNT(DISTINCT tgl) as unique_dates,
                    COUNT(CASE WHEN masuk IS NOT NULL THEN 1 END) as records_with_masuk,
                    COUNT(CASE WHEN keluar IS NOT NULL THEN 1 END) as records_with_keluar,
                    COUNT(CASE WHEN masuk IS NOT NULL AND keluar IS NOT NULL THEN 1 END) as complete_records
                FROM attrecords
                {where_clause}
            """
            
            cursor.execute(summary_query, params)
            result = cursor.fetchone()
            
            summary = {
                'total_records': result[0] or 0,
                'unique_employees': result[1] or 0,
                'unique_dates': result[2] or 0,
                'records_with_masuk': result[3] or 0,
                'records_with_keluar': result[4] or 0,
                'complete_records': result[5] or 0
            }
            
            cursor.close()
            conn.close()
            
            return summary
            
        except Exception as e:
            print(f"Error getting summary stats: {e}")
            return {}
