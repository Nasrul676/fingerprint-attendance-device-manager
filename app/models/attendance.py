from config.database import db_manager
from datetime import datetime

class AttendanceModel:
    """Model for handling attendance data operations"""
    
    def __init__(self):
        self.db_manager = db_manager
    
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
    
    def check_fplog_duplicate(self, pin, date, status):
        """Check if FPLog record already exists with same PIN, Date, and Status"""
        try:
            conn = self.db_manager.get_sqlserver_connection()
            if not conn:
                return False, "Database connection failed"
            
            cursor = conn.cursor()
            
            # Check for exact match: PIN, Date (down to minute), and Status
            check_query = """
                SELECT COUNT(*) as count
                FROM FPLog
                WHERE PIN = ? 
                AND CONVERT(varchar(16), Date, 120) = CONVERT(varchar(16), ?, 120)
                AND Status = ?
            """
            
            cursor.execute(check_query, (str(pin), date, str(status)))
            result = cursor.fetchone()
            count = result[0] if result else 0
            
            cursor.close()
            conn.close()
            
            return count > 0, f"Found {count} existing records"
            
        except Exception as e:
            return False, f"Error checking duplicate: {str(e)}"
    
    def bulk_check_fplog_duplicates(self, records):
        """Bulk check for FPLog duplicates and return non-duplicate records only"""
        try:
            if not records:
                return [], 0, 0
            
            conn = self.db_manager.get_sqlserver_connection()
            if not conn:
                return records, 0, 0  # Return all if can't check
            
            cursor = conn.cursor()
            
            # Build bulk check query with UNION ALL for better performance
            check_queries = []
            check_params = []
            
            for i, record in enumerate(records):
                pin = str(record.get('PIN', ''))
                date = record.get('Date', '')
                status = str(record.get('Status', ''))
                
                check_queries.append(f"""
                    SELECT ? as idx, COUNT(*) as count
                    FROM FPLog
                    WHERE PIN = ? 
                    AND CONVERT(varchar(16), Date, 120) = CONVERT(varchar(16), ?, 120)
                    AND Status = ?
                """)
                check_params.extend([i, pin, date, status])
            
            if check_queries:
                full_query = " UNION ALL ".join(check_queries)
                cursor.execute(full_query, check_params)
                results = cursor.fetchall()
                
                # Create set of duplicate indices
                duplicate_indices = set()
                for result in results:
                    idx, count = result
                    if count > 0:
                        duplicate_indices.add(idx)
                
                # Filter out duplicates
                non_duplicate_records = []
                for i, record in enumerate(records):
                    if i not in duplicate_indices:
                        non_duplicate_records.append(record)
                
                cursor.close()
                conn.close()
                
                duplicates_found = len(duplicate_indices)
                records_kept = len(non_duplicate_records)
                
                return non_duplicate_records, duplicates_found, records_kept
            else:
                cursor.close()
                conn.close()
                return records, 0, len(records)
                
        except Exception as e:
            print(f"Error in bulk duplicate check: {str(e)}")
            # Return all records if error occurs
            return records, 0, len(records)
    
    def sync_fplog_to_sqlserver_with_duplicate_check(self, fplog_data, start_date=None, end_date=None):
        """Sync FPLog data from fingerprint devices to SQL Server with duplicate prevention"""
        try:
            # Validate input data
            if not fplog_data or not isinstance(fplog_data, list):
                return False, "Invalid or empty FPLog data provided"
            
            print(f"Starting sync of {len(fplog_data)} FPLog records with duplicate check...")
            
            # Step 1: Filter out duplicates
            filtered_data, duplicates_found, records_kept = self.bulk_check_fplog_duplicates(fplog_data)
            
            print(f"Duplicate check completed: {duplicates_found} duplicates found, {records_kept} records to insert")
            
            if not filtered_data:
                return True, f"All {len(fplog_data)} records were duplicates - no new data to sync"
            
            conn = self.db_manager.get_sqlserver_connection()
            if not conn:
                return False, "Failed to connect to SQL Server"
            
            cursor = conn.cursor()
            
            # Step 2: Insert only non-duplicate data
            insert_query = """
                INSERT INTO FPLog (PIN, Date, Machine, Status, fpid)
                VALUES (?, ?, ?, ?, ?)
            """
            
            # Process data in batches for better performance
            batch_size = 5000
            total_inserted = 0
            
            for i in range(0, len(filtered_data), batch_size):
                batch = filtered_data[i:i + batch_size]
                batch_values = []
                
                for record in batch:
                    # Ensure proper data type conversion
                    pin = str(record.get('PIN', '')) if record.get('PIN') is not None else ''
                    date_val = record.get('Date', '')
                    machine = str(record.get('Machine', '')) if record.get('Machine') is not None else ''
                    status = record.get('Status', 'I')  # Default to 'I' if no status
                    
                    # Convert fpid to integer
                    try:
                        fpid = int(record.get('fpid', None))
                    except (ValueError, TypeError):
                        fpid = None
                    
                    # Validate date format
                    if date_val and isinstance(date_val, str):
                        try:
                            from datetime import datetime
                            if len(date_val) == 19:
                                datetime.strptime(date_val, '%Y-%m-%d %H:%M:%S')
                            elif len(date_val) == 16:
                                date_val += ':00'
                            elif len(date_val) == 10:
                                date_val += ' 00:00:00'
                        except ValueError:
                            print(f"Warning: Invalid date format for record: {date_val}")
                            continue
                    elif not date_val:
                        print(f"Warning: Empty date for record, skipping")
                        continue
                    
                    batch_values.append((pin, date_val, machine, status, fpid))
                
                if batch_values:
                    cursor.executemany(insert_query, batch_values)
                    total_inserted += cursor.rowcount
            
            conn.commit()
            cursor.close()
            conn.close()
            
            print(f"Sync completed: {total_inserted} new records inserted, {duplicates_found} duplicates skipped")
            return True, f"Successfully synced {total_inserted} new records (skipped {duplicates_found} duplicates)"
            
        except Exception as e:
            print(f"Error details: {str(e)}")
            try:
                if 'cursor' in locals():
                    cursor.close()
                if 'conn' in locals():
                    conn.close()
            except:
                pass
            return False, f"Error syncing FPLog data: {str(e)}"
    
    def add_fplog_record_if_not_duplicate(self, pin, date, machine, status, fpid=None):
        """Add single FPLog record only if it's not a duplicate"""
        try:
            # Check for duplicate first
            is_duplicate, message = self.check_fplog_duplicate(pin, date, status)
            
            if is_duplicate:
                return False, f"Duplicate record found - not inserted: PIN={pin}, Date={date}, Status={status}"
            
            # Insert the record
            conn = self.db_manager.get_sqlserver_connection()
            if not conn:
                return False, "Failed to connect to SQL Server"
            
            cursor = conn.cursor()
            
            insert_query = """
                INSERT INTO FPLog (PIN, Date, Machine, Status, fpid)
                VALUES (?, ?, ?, ?, ?)
            """
            
            # Ensure proper data types
            pin = str(pin) if pin is not None else ''
            machine = str(machine) if machine is not None else ''
            status = str(status) if status is not None else 'I'
            fpid = int(fpid) if fpid is not None else None
            
            cursor.execute(insert_query, (pin, date, machine, status, fpid))
            conn.commit()
            
            cursor.close()
            conn.close()
            
            return True, f"Record inserted successfully: PIN={pin}, Date={date}, Status={status}"
            
        except Exception as e:
            return False, f"Error adding FPLog record: {str(e)}"
    
    def check_attendance_queue_duplicate(self, pin, date, machine):
        """Check if attendance_queue record already exists with same PIN, Date (down to minute), and Machine"""
        try:
            conn = self.db_manager.get_sqlserver_connection()
            if not conn:
                return False, "Database connection failed"
            
            cursor = conn.cursor()
            
            # Check for exact match: PIN, Date (down to minute), and Machine
            check_query = """
                SELECT COUNT(*) as count
                FROM attendance_queues
                WHERE pin = ? 
                AND CONVERT(varchar(16), date, 120) = CONVERT(varchar(16), ?, 120)
                AND machine = ?
            """
            
            cursor.execute(check_query, (str(pin), date, str(machine)))
            result = cursor.fetchone()
            count = result[0] if result else 0
            
            cursor.close()
            conn.close()
            
            return count > 0, f"Found {count} existing records"
            
        except Exception as e:
            return False, f"Error checking duplicate: {str(e)}"
    
    def add_to_attendance_queue_if_not_duplicate(self, pin, date, status='baru', machine=None, punch_code=None):
        """Add attendance record to queue only if it's not a duplicate"""
        try:
            # Check for duplicate first if machine is provided
            if machine:
                is_duplicate, message = self.check_attendance_queue_duplicate(pin, date, machine)
                
                if is_duplicate:
                    return False, f"Duplicate record found - not inserted: PIN={pin}, Date={date}, Machine={machine}"
            
            # Insert the record using existing method
            return self.add_to_attendance_queue(pin, date, status, machine, punch_code)
            
        except Exception as e:
            return False, f"Error adding to attendance queue: {str(e)}"
    
    def get_failed_attendance_logs(self, start_date=None, end_date=None, page=1, per_page=50):
        """Get failed attendance logs from gagalabsens table with pagination"""
        try:
            conn = self.db_manager.get_sqlserver_connection()
            if not conn:
                return [], 0, 0
            
            cursor = conn.cursor()
            
            # Build filter query
            filter_query = ""
            params = []
            if start_date and end_date:
                filter_query = " WHERE tgl BETWEEN ? AND ?"
                params = [start_date + ' 00:00:00', end_date + ' 23:59:59']
            elif start_date:
                filter_query = " WHERE tgl >= ?"
                params = [start_date + ' 00:00:00']
            elif end_date:
                filter_query = " WHERE tgl <= ?"
                params = [end_date + ' 23:59:59']
            
            # Get total count
            count_query = f"SELECT COUNT(*) as total FROM gagalabsens{filter_query}"
            cursor.execute(count_query, params)
            total = cursor.fetchone()[0]
            
            # Get paginated data
            offset = (page - 1) * per_page
            data_query = f"""
                SELECT id, pin, tgl, machine, status, created_at, updated_at
                FROM gagalabsens
                {filter_query}
                ORDER BY tgl DESC
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
                    if hasattr(value, 'strftime') and value is not None:
                        row_dict[columns[i]] = value.strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        row_dict[columns[i]] = value
                data.append(row_dict)
            
            cursor.close()
            conn.close()
            
            total_pages = (total + per_page - 1) // per_page
            return data, total, total_pages
            
        except Exception as e:
            print(f"Error getting failed attendance logs: {e}")
            return [], 0, 0
    
    def get_failed_attendance_stats(self):
        """Get statistics for failed attendance logs"""
        try:
            conn = self.db_manager.get_sqlserver_connection()
            if not conn:
                return {}
            
            cursor = conn.cursor()
            
            # Get total count
            cursor.execute("SELECT COUNT(*) as total FROM gagalabsens")
            total = cursor.fetchone()[0]
            
            # Get count by status
            cursor.execute("""
                SELECT status, COUNT(*) as count 
                FROM gagalabsens 
                GROUP BY status 
                ORDER BY count DESC
            """)
            status_counts = {}
            for row in cursor.fetchall():
                status_counts[row[0]] = row[1]
            
            # Get count by machine
            cursor.execute("""
                SELECT machine, COUNT(*) as count 
                FROM gagalabsens 
                GROUP BY machine 
                ORDER BY count DESC
            """)
            machine_counts = {}
            for row in cursor.fetchall():
                machine_counts[row[0]] = row[1]
            
            # Get recent failed attendance (last 7 days)
            cursor.execute("""
                SELECT COUNT(*) as recent_count 
                FROM gagalabsens 
                WHERE tgl >= DATEADD(day, -7, GETDATE())
            """)
            recent_count = cursor.fetchone()[0]
            
            cursor.close()
            conn.close()
            
            return {
                'total': total,
                'status_counts': status_counts,
                'machine_counts': machine_counts,
                'recent_count': recent_count
            }
            
        except Exception as e:
            print(f"Error getting failed attendance stats: {e}")
            return {}
