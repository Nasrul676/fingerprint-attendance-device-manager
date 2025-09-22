from config.database import db_manager
from flask import current_app

class WorkerModel:
    def execute_recalculation_procedure(self, start_date, end_date):
        """
        Executes 'attrecord' and 'spJamkerja' stored procedures for a given date range.
        
        Args:
            start_date (str): The start date in 'YYYY-MM-DD' format.
            end_date (str): The end date in 'YYYY-MM-DD' format.
            
        Returns:
            tuple: (bool, str) indicating success and a message.
        """
        try:
            conn = db_manager.get_sqlserver_connection()
            if not conn:
                return False, "Database connection failed."
            
            cursor = conn.cursor()
            
            # Convert date format from YYYY-MM-DD to YYYYMMDD
            start_date_formatted = start_date.replace('-', '')
            end_date_formatted = end_date.replace('-', '')
            
            # List of procedures to execute
            procedure_names = ['attrecord', 'spJamkerja']
            
            for procedure_name in procedure_names:
                current_app.logger.info(f"Executing stored procedure '{procedure_name}' with range: {start_date_formatted} to {end_date_formatted}")
                
                # Execute the stored procedure with correct parameters and date format
                cursor.execute(f"EXEC {procedure_name} @awal=?, @akhir=?", (start_date_formatted, end_date_formatted))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            success_message = f"Prosedur 'attrecord' dan 'spJamkerja' berhasil dijalankan untuk rentang tanggal {start_date} hingga {end_date}."
            current_app.logger.info(success_message)
            return True, success_message
            
        except Exception as e:
            error_message = f"Error executing stored procedure: {e}"
            current_app.logger.error(error_message)
            return False, error_message

# Instantiate the model
worker_model = WorkerModel()