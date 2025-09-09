from config.database import db_manager
from datetime import datetime

class AttendanceModel:
    """Model for handling attendance data operations"""
    
    def __init__(self):
        self.db_manager = db_manager
    
    def get_attendance_logs(self, start_date=None, end_date=None, page=1, per_page=20):
        """Get attendance logs with pagination and optional date filtering"""
        try:
            conn = self.db_manager.get_sqlserver_connection()
            if not conn:
                return [], 0, 0
            
            cursor = conn.cursor()
            
            # Build filter query
            filter_query = ''
            params = []
            if start_date:
                filter_query += ' AND timestamp >= ?'
                params.append(start_date + ' 00:00:00')
            if end_date:
                filter_query += ' AND timestamp <= ?'
                params.append(end_date + ' 23:59:59')
            
            # Get total count
            count_query = f"SELECT COUNT(*) as count FROM log_absensi WHERE 1=1 {filter_query}"
            cursor.execute(count_query, params)
            total = cursor.fetchone()[0]
            total_pages = (total + per_page - 1) // per_page
            
            # Get paginated data
            offset = (page - 1) * per_page
            data_query = (
                "SELECT user_id, timestamp, status "
                "FROM log_absensi "
                f"WHERE 1=1 {filter_query} "
                "ORDER BY timestamp DESC "
                f"OFFSET {offset} ROWS FETCH NEXT {per_page} ROWS ONLY"
            )
            cursor.execute(data_query, params)
            
            # Convert to list of dictionaries
            columns = [column[0] for column in cursor.description]
            rows = cursor.fetchall()
            logs = []
            for row in rows:
                log_dict = {}
                for i, value in enumerate(row):
                    log_dict[columns[i]] = value
                logs.append(log_dict)
            
            cursor.close()
            conn.close()
            
            return logs, total, total_pages
            
        except Exception as e:
            print(f"Error getting attendance logs: {e}")
            return [], 0, 0
    
    def get_fplog_data(self, start_date=None, end_date=None, page=1, per_page=50):
        """Get FPLog data from SQL Server"""
        try:
            conn = self.db_manager.get_sqlserver_connection()
            if not conn:
                return [], 0, 0
            
            cursor = conn.cursor()
            
            # Build filter query
            filter_query = ""
            params = []
            if start_date and end_date:
                filter_query = " WHERE Date BETWEEN ? AND ?"
                params = [start_date, end_date]
            
            # Get total count
            count_query = f"SELECT COUNT(*) as total FROM FPLog{filter_query}"
            cursor.execute(count_query, params)
            total = cursor.fetchone()[0]
            
            # Get paginated data
            offset = (page - 1) * per_page
            data_query = f"""
                SELECT PIN, Date, Machine, Status, fpid
                FROM FPLog
                {filter_query}
                ORDER BY Date DESC
                OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
            """
            params.extend([offset, per_page])
            cursor.execute(data_query, params)
            
            # Convert to list of dictionaries
            columns = [column[0] for column in cursor.description]
            rows = cursor.fetchall()
            data = []
            for row in rows:
                row_dict = {}
                for i, value in enumerate(row):
                    if hasattr(value, 'strftime'):
                        row_dict[columns[i]] = value.strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        row_dict[columns[i]] = value
                data.append(row_dict)
            
            cursor.close()
            conn.close()
            
            total_pages = (total + per_page - 1) // per_page
            return data, total, total_pages
            
        except Exception as e:
            print(f"Error getting FPLog data: {e}")
            return [], 0, 0
    
    def execute_attrecord_procedure(self, start_date, end_date):
        """Execute the attrecord stored procedure"""
        try:
            conn = self.db_manager.get_sqlserver_connection()
            if not conn:
                return False, "Failed to connect to SQL Server"
            
            cursor = conn.cursor()
            query = "EXEC [dbo].[attrecord] ?, ?"
            cursor.execute(query, (start_date, end_date))
            conn.commit()
            
            cursor.close()
            conn.close()
            
            return True, "Procedure executed successfully"
            
        except Exception as e:
            return False, f"Error executing procedure: {str(e)}"
    
    def execute_spjamkerja_procedure(self, start_date, end_date):
        """Execute the spJamkerja stored procedure"""
        try:
            conn = self.db_manager.get_sqlserver_connection()
            if not conn:
                return False, "Failed to connect to SQL Server"
            
            cursor = conn.cursor()
            query = "EXEC [dbo].[spJamkerja] ?, ?"
            cursor.execute(query, (start_date, end_date))
            conn.commit()
            
            cursor.close()
            conn.close()
            
            return True, "Procedure executed successfully"
            
        except Exception as e:
            return False, f"Error executing procedure: {str(e)}"
    
    def sync_fplog_to_sqlserver(self, fplog_data, start_date=None, end_date=None):
        """Sync FPLog data from fingerprint devices to SQL Server with duplicate removal"""
        try:
            # Validate input data
            if not fplog_data or not isinstance(fplog_data, list):
                return False, "Invalid or empty FPLog data provided"
            
            print(f"Starting sync of {len(fplog_data)} FPLog records to SQL Server...")
            
            conn = self.db_manager.get_sqlserver_connection()
            if not conn:
                return False, "Failed to connect to SQL Server"
            
            cursor = conn.cursor()
            
            # Step 1: Delete existing data for the date range and machines to prevent duplicates
            if fplog_data:
                # Get unique machines from the data
                machines = list(set(record.get('Machine', '') for record in fplog_data))
                machines_placeholder = ','.join(['?'] * len(machines))
                
                if start_date and end_date:
                    # Delete specific date range for specific machines
                    delete_query = f"""
                        DELETE FROM FPLog 
                        WHERE Machine IN ({machines_placeholder})
                        AND CAST(Date AS DATE) BETWEEN ? AND ?
                    """
                    delete_params = machines + [start_date, end_date]
                    cursor.execute(delete_query, delete_params)
                    deleted_count = cursor.rowcount
                    print(f"Deleted {deleted_count} existing records for machines {machines} between {start_date} and {end_date}")
                else:
                    # If no date filter, get date range from the data itself
                    dates = [record.get('Date', '') for record in fplog_data if record.get('Date')]
                    if dates:
                        min_date = min(dates).split(' ')[0]  # Get date part only
                        max_date = max(dates).split(' ')[0]  # Get date part only
                        
                        delete_query = f"""
                            DELETE FROM FPLog 
                            WHERE Machine IN ({machines_placeholder})
                            AND CAST(Date AS DATE) BETWEEN ? AND ?
                        """
                        delete_params = machines + [min_date, max_date]
                        cursor.execute(delete_query, delete_params)
                        deleted_count = cursor.rowcount
                        print(f"Deleted {deleted_count} existing records for machines {machines} between {min_date} and {max_date}")
            
            # Step 2: Insert new FPLog data
            insert_query = """
                INSERT INTO FPLog (PIN, Date, Machine, Status, fpid)
                VALUES (?, ?, ?, ?, ?)
            """
            
            # Process data in batches for better performance
            batch_size = 1000
            total_inserted = 0
            
            for i in range(0, len(fplog_data), batch_size):
                batch = fplog_data[i:i + batch_size]
                batch_values = []
                
                for record in batch:
                    # Ensure proper data type conversion
                    pin = str(record.get('PIN', '')) if record.get('PIN') is not None else ''
                    date_val = record.get('Date', '')
                    machine = str(record.get('Machine', '')) if record.get('Machine') is not None else ''
                    
                    # Convert Status to integer
                    try:
                        status = int(record.get('Status', 0))
                    except (ValueError, TypeError):
                        status = 0
                    
                    # Convert fpid to integer
                    try:
                        fpid = int(record.get('fpid', 0))
                    except (ValueError, TypeError):
                        fpid = 0
                    
                    # Validate date format
                    if date_val and isinstance(date_val, str):
                        # Ensure date is in proper format
                        try:
                            # Try to parse and reformat if needed
                            from datetime import datetime
                            if len(date_val) == 19:  # YYYY-MM-DD HH:MM:SS format
                                datetime.strptime(date_val, '%Y-%m-%d %H:%M:%S')
                            elif len(date_val) == 16:  # YYYY-MM-DD HH:MM format
                                date_val += ':00'
                            elif len(date_val) == 10:  # YYYY-MM-DD format
                                date_val += ' 00:00:00'
                        except ValueError:
                            print(f"Warning: Invalid date format for record: {date_val}")
                            continue  # Skip this record
                    elif not date_val:
                        print(f"Warning: Empty date for record, skipping")
                        continue  # Skip records with empty dates
                    
                    batch_values.append((pin, date_val, machine, status, fpid))
                
                if batch_values:  # Only execute if we have valid records
                    cursor.executemany(insert_query, batch_values)
                    total_inserted += cursor.rowcount
            
            conn.commit()
            cursor.close()
            conn.close()
            
            print(f"Sync completed: {total_inserted} records inserted")
            return True, f"Successfully synced {total_inserted} records (deleted {deleted_count if 'deleted_count' in locals() else 0} duplicates)"
            
        except Exception as e:
            print(f"Error details: {str(e)}")
            # Try to close connections on error
            try:
                if 'cursor' in locals():
                    cursor.close()
                if 'conn' in locals():
                    conn.close()
            except:
                pass
            return False, f"Error syncing FPLog data: {str(e)}"
    
    def get_device_sync_status(self):
        """Get synchronization status for each device"""
        try:
            conn = self.db_manager.get_sqlserver_connection()
            if not conn:
                return []
            
            cursor = conn.cursor()
            
            # Get last sync time for each machine
            query = """
                SELECT 
                    Machine,
                    COUNT(*) as total_records,
                    MAX(Date) as last_sync,
                    MIN(Date) as first_record
                FROM FPLog
                GROUP BY Machine
                ORDER BY Machine
            """
            cursor.execute(query)
            
            # Convert to list of dictionaries
            columns = [column[0] for column in cursor.description]
            rows = cursor.fetchall()
            status = []
            for row in rows:
                status_dict = {}
                for i, value in enumerate(row):
                    status_dict[columns[i]] = value
                status.append(status_dict)
            
            cursor.close()
            conn.close()
            
            return status
            
        except Exception as e:
            print(f"Error getting device sync status: {e}")
            return []
    
    def create_attendance_queues_table(self):
        """Create attendance_queues table if it doesn't exist"""
        try:
            conn = self.db_manager.get_sqlserver_connection()
            if not conn:
                return False, "Database connection failed"
            
            cursor = conn.cursor()
            
            # Create attendance_queues table
            create_table_query = """
                IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='attendance_queues' AND xtype='U')
                CREATE TABLE attendance_queues (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    pin VARCHAR(50) NOT NULL,
                    date DATETIME NOT NULL,
                    status VARCHAR(10) NOT NULL DEFAULT 'baru',
                    machine VARCHAR(50) NULL,
                    punch_code INT NULL,
                    created_at DATETIME DEFAULT GETDATE(),
                    updated_at DATETIME DEFAULT GETDATE()
                );
                
                IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name='idx_pin_attendance_queues')
                CREATE INDEX idx_pin_attendance_queues ON attendance_queues (pin);
                
                IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name='idx_date_attendance_queues')
                CREATE INDEX idx_date_attendance_queues ON attendance_queues (date);
                
                IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name='idx_status_attendance_queues')
                CREATE INDEX idx_status_attendance_queues ON attendance_queues (status);
            """
            
            cursor.execute(create_table_query)
            conn.commit()
            cursor.close()
            conn.close()
            
            return True, "attendance_queues table created successfully"
            
        except Exception as e:
            return False, f"Error creating attendance_queues table: {str(e)}"
    
    def add_to_attendance_queue(self, pin, date, status='baru', machine=None, punch_code=None):
        """Add attendance record to queue"""
        try:
            # Validate input parameters
            pin = str(pin) if pin is not None else ''
            status = str(status) if status is not None else 'baru'
            
            if machine is not None:
                machine = str(machine)
            
            if punch_code is not None:
                try:
                    punch_code = int(punch_code)
                except (ValueError, TypeError):
                    print(f"Warning: Invalid punch_code '{punch_code}', setting to None")
                    punch_code = None
            
            conn = self.db_manager.get_sqlserver_connection()
            if not conn:
                return False, "Database connection failed"
            
            cursor = conn.cursor()
            
            # Insert into attendance_queues
            insert_query = """
                INSERT INTO attendance_queues (pin, date, status, machine, punch_code)
                VALUES (?, ?, ?, ?, ?)
            """
            
            cursor.execute(insert_query, (pin, date, status, machine, punch_code))
            cursor.execute("SELECT @@IDENTITY")
            queue_id = cursor.fetchone()[0]
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return True, f"Added to queue with ID: {queue_id}"
            
        except Exception as e:
            return False, f"Error adding to attendance queue: {str(e)}"
    
    def bulk_add_to_attendance_queue(self, attendance_records):
        """Bulk add attendance records to queue"""
        try:
            conn = self.db_manager.get_sqlserver_connection()
            if not conn:
                return False, "Database connection failed"
            
            cursor = conn.cursor()
            
            # Prepare bulk insert
            insert_query = """
                INSERT INTO attendance_queues (pin, date, status, machine, punch_code)
                VALUES (?, ?, ?, ?, ?)
            """
            
            batch_values = []
            for record in attendance_records:
                # Validate and convert punch_code to integer
                punch_code = record.get('punch_code', None)
                if punch_code is not None:
                    try:
                        # Convert punch_code to integer, skip invalid values
                        punch_code = int(punch_code)
                    except (ValueError, TypeError):
                        print(f"Warning: Invalid punch_code '{punch_code}' in record, setting to None")
                        punch_code = None
                
                # Ensure pin is string
                pin = str(record.get('pin', '')) if record.get('pin') is not None else ''
                
                # Ensure status is string
                status = str(record.get('status', 'baru'))
                
                # Ensure machine is string or None
                machine = record.get('machine', None)
                if machine is not None:
                    machine = str(machine)
                
                # Validate date
                date = record.get('date', '')
                if not date:
                    print(f"Warning: Empty date in record, skipping")
                    continue
                
                batch_values.append((pin, date, status, machine, punch_code))
            
            # Only execute if we have valid records
            if not batch_values:
                return False, "No valid records to insert"
            
            cursor.executemany(insert_query, batch_values)
            inserted_count = cursor.rowcount
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return True, f"Bulk added {inserted_count} records to attendance queue"
            
        except Exception as e:
            return False, f"Error bulk adding to attendance queue: {str(e)}"
    
    def get_attendance_queue(self, status=None, limit=100):
        """Get attendance records from queue"""
        try:
            conn = self.db_manager.get_sqlserver_connection()
            if not conn:
                return []
            
            cursor = conn.cursor()
            
            # Build query with optional status filter
            query = """
                SELECT id, pin, date, status, machine, punch_code, created_at
                FROM attendance_queues
            """
            params = []
            
            if status:
                query += " WHERE status = ?"
                params.append(status)
            
            query += " ORDER BY created_at ASC OFFSET 0 ROWS FETCH NEXT ? ROWS ONLY"
            params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            # Convert to dictionary manually
            columns = [column[0] for column in cursor.description]
            queue_records = [dict(zip(columns, row)) for row in rows]
            
            cursor.close()
            conn.close()
            
            return queue_records
            
        except Exception as e:
            print(f"Error getting attendance queue: {e}")
            return []
    
    def update_queue_status(self, queue_id, new_status):
        """Update status of queue record"""
        try:
            conn = self.db_manager.get_sqlserver_connection()
            if not conn:
                return False, "Database connection failed"
            
            cursor = conn.cursor()
            
            update_query = """
                UPDATE attendance_queues 
                SET status = ?, updated_at = GETDATE()
                WHERE id = ?
            """
            
            cursor.execute(update_query, (new_status, queue_id))
            affected_rows = cursor.rowcount
            
            conn.commit()
            cursor.close()
            conn.close()
            
            if affected_rows > 0:
                return True, f"Queue record {queue_id} status updated to {new_status}"
            else:
                return False, f"Queue record {queue_id} not found"
                
        except Exception as e:
            return False, f"Error updating queue status: {str(e)}"
    
    def delete_from_queue(self, queue_id):
        """Delete record from attendance queue"""
        try:
            conn = self.db_manager.get_sqlserver_connection()
            if not conn:
                return False, "Database connection failed"
            
            cursor = conn.cursor()
            
            delete_query = "DELETE FROM attendance_queues WHERE id = ?"
            cursor.execute(delete_query, (queue_id,))
            affected_rows = cursor.rowcount
            
            conn.commit()
            cursor.close()
            conn.close()
            
            if affected_rows > 0:
                return True, f"Queue record {queue_id} deleted successfully"
            else:
                return False, f"Queue record {queue_id} not found"
                
        except Exception as e:
            return False, f"Error deleting from queue: {str(e)}"
