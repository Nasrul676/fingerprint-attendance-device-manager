import pyodbc
from config.config import config
import os
import logging

class DatabaseManager:
    """Database connection manager for SQL Server"""
    
    def __init__(self, config_name='development'):
        self.config = config[config_name]
        self.config_name = config_name
        self.logger = logging.getLogger('DatabaseManager')
    
    def get_sqlserver_connection(self):
        """Get SQL Server database connection"""
        try:
            # Validate required configuration for production
            if self.config_name == 'production':
                required_fields = ['SQLSERVER_HOST', 'SQLSERVER_DATABASE', 'SQLSERVER_USERNAME', 'SQLSERVER_PASSWORD']
                for field in required_fields:
                    if not getattr(self.config, field):
                        raise ValueError(f"Missing required configuration: {field}")
            
            connection_string = (
                f"DRIVER={self.config.SQLSERVER_DRIVER};"
                f"SERVER={self.config.SQLSERVER_HOST};"
                f"DATABASE={self.config.SQLSERVER_DATABASE};"
                f"UID={self.config.SQLSERVER_USERNAME};"
                f"PWD={self.config.SQLSERVER_PASSWORD};"
                f"TrustServerCertificate=yes;"  # For development, remove in production with proper SSL
                f"Timeout=30;"
            )
            
            connection = pyodbc.connect(connection_string)
            connection.autocommit = False
            
            if self.config_name == 'production':
                self.logger.info("SQL Server connection established (production)")
            
            return connection
            
        except Exception as e:
            error_msg = f"SQL Server Connection Error: {e}"
            if self.config_name == 'production':
                self.logger.error(error_msg)
            else:
                print(error_msg)
            return None
    
    def get_connection(self):
        """Alias for get_sqlserver_connection for backwards compatibility"""
        return self.get_sqlserver_connection()
    
    def test_connection(self):
        """Test SQL Server database connection"""
        try:
            conn = self.get_sqlserver_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()
                cursor.close()
                conn.close()
                print("✅ SQL Server connection: OK")
                return True
            else:
                print("❌ SQL Server connection: FAILED")
                return False
        except Exception as e:
            print(f"❌ SQL Server connection test failed: {e}")
            return False

# Global database manager instance
db_manager = DatabaseManager(os.environ.get('FLASK_ENV', 'development'))
