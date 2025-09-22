import os
import secrets
import pyodbc
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Base configuration class"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_urlsafe(32)
    DEBUG = False
    TESTING = False
    
    # Security Headers
    SEND_FILE_MAX_AGE_DEFAULT = 31536000  # 1 year for static files
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Application Settings
    JSON_SORT_KEYS = False
    JSONIFY_PRETTYPRINT_REGULAR = False
    
    def get_available_odbc_drivers(self):
        """Get list of available SQL Server ODBC drivers"""
        drivers = pyodbc.drivers()
        sql_server_drivers = [d for d in drivers if 'SQL Server' in d]
        return sql_server_drivers
    
    def get_best_odbc_driver(self):
        """Get the configured ODBC driver and verify it's installed."""
        available_drivers = self.get_available_odbc_drivers()
        
        # Get the driver name from the configuration, stripping any braces.
        configured_driver = getattr(self, 'SQLSERVER_DRIVER', '').strip('{}')
        
        if not configured_driver:
            raise ValueError("SQLSERVER_DRIVER is not configured in .env or config.py")
            
        if configured_driver not in available_drivers:
            available = ' | '.join(available_drivers) if available_drivers else "None"
            raise pyodbc.InterfaceError(
                f"Configured driver '{configured_driver}' not found. "
                f"Available drivers: [{available}]. "
                "Please install 'ODBC Driver 17 for SQL Server' or update SQLSERVER_DRIVER in .env"
            )
            
        return configured_driver

    def get_sql_server_connection_string(self):
        """Build SQL Server connection string using SQL Server Authentication"""
        driver = self.get_best_odbc_driver()
        
        # Construct server with explicit port 1433
        server_with_port = self.SQLSERVER_HOST
        if ':' not in server_with_port and '\\' not in server_with_port and ',' not in server_with_port:
            server_with_port = f"{self.SQLSERVER_HOST},1433"
        
        # Force SQL Server Authentication (not Windows Authentication)
        conn_str = (
            f"DRIVER={{{driver}}};"
            f"SERVER={server_with_port};"
            f"DATABASE={self.SQLSERVER_DATABASE};"
            f"UID={self.SQLSERVER_USERNAME};"
            f"PWD={self.SQLSERVER_PASSWORD};"
            "Connection Timeout=30;"
        )
        
        # Add encryption settings based on driver version - be more conservative
        if "Driver 18" in driver:
            conn_str += "TrustServerCertificate=yes;Encrypt=Optional;"
        elif "Driver 17" in driver:
            conn_str += "TrustServerCertificate=yes;Encrypt=no;"
        elif "Driver 13" in driver:
            # For Driver 13, be very minimal with options
            pass  # No additional encryption parameters
        elif "Driver 11" in driver or "Native Client" in driver:
            # Older drivers - minimal options
            pass
        else:
            # Very old drivers - no encryption options
            pass
        
        return conn_str
    
    def test_database_connection(self):
        """Test database connection using SQL Server Authentication"""
        try:
            # This will now raise a specific error if the driver is not found.
            selected_driver = self.get_best_odbc_driver()
            
            # Build connection string with SQL Server Authentication
            conn_str = self.get_sql_server_connection_string()
            
            # Test connection with very simple query
            with pyodbc.connect(conn_str, timeout=30) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                
                if result and result[0] == 1:
                    return True, f"✅ Connection successful using driver: {selected_driver}. Database: {self.SQLSERVER_DATABASE}"
                else:
                    return False, "Database query failed"
                    
        except pyodbc.InterfaceError as e:
            # This will now catch the specific driver error from get_best_odbc_driver
            return False, f"ODBC Driver Error: {str(e)}"
        except pyodbc.DatabaseError as e:
            error_msg = str(e)
            if "18456" in error_msg:
                return False, (
                    f"Authentication failed for user '{self.SQLSERVER_USERNAME}'. "
                    "Check: 1) SQL Server Mixed Mode auth enabled, 2) sa account enabled, 3) Correct password"
                )
            elif "4060" in error_msg or "cannot open database" in error_msg.lower():
                return False, f"Database '{self.SQLSERVER_DATABASE}' not found. Create it in SQL Server Management Studio."
            else:
                return False, f"Database Error: {error_msg}"
        except pyodbc.Error as e:
            error_msg = str(e)
            if "08001" in error_msg:
                return False, f"Cannot connect to SQL Server at '{self.SQLSERVER_HOST}'. Check if SQL Server is running and TCP/IP enabled."
            else:
                return False, f"Connection Error: {error_msg}"
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"

    def create_database_connection(self):
        """Create and return a database connection"""
        try:
            # This will now raise a clear error if the driver is missing
            conn_str = self.get_sql_server_connection_string()
            return pyodbc.connect(conn_str, timeout=30)
        except Exception as e:
            logging.error(f"Failed to create database connection: {str(e)}")
            raise

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    
    # SQL Server Database Configuration
    SQLSERVER_HOST = os.environ.get('SQLSERVER_HOST') or 'localhost'
    SQLSERVER_DATABASE = os.environ.get('SQLSERVER_DATABASE') or 'HRAPP'
    SQLSERVER_USERNAME = os.environ.get('SQLSERVER_USERNAME') or 'sa'
    SQLSERVER_PASSWORD = os.environ.get('SQLSERVER_PASSWORD') or 'Pkppastibisa-2025'
    # Explicitly set the desired driver. This will be used unless overridden by .env
    SQLSERVER_DRIVER = os.environ.get('SQLSERVER_DRIVER') or 'ODBC Driver 17 for SQL Server'

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    
    # Security settings for production
    SESSION_COOKIE_SECURE = True
    PREFERRED_URL_SCHEME = 'https'
    
    # Ensure all required environment variables are set
    SQLSERVER_HOST = os.environ.get('SQLSERVER_HOST') or None
    SQLSERVER_DATABASE = os.environ.get('SQLSERVER_DATABASE') or None
    SQLSERVER_USERNAME = os.environ.get('SQLSERVER_USERNAME') or None
    SQLSERVER_PASSWORD = os.environ.get('SQLSERVER_PASSWORD') or None
    SQLSERVER_DRIVER = os.environ.get('SQLSERVER_DRIVER') or 'ODBC Driver 17 for SQL Server'
    
    @classmethod
    def validate_config(cls):
        """Validate that all required production environment variables are set"""
        required_vars = [
            'SECRET_KEY',
            'SQLSERVER_HOST', 
            'SQLSERVER_DATABASE',
            'SQLSERVER_USERNAME',
            'SQLSERVER_PASSWORD'
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.environ.get(var):
                missing_vars.append(var)
        
        if missing_vars:
            raise EnvironmentError(
                f"Missing required environment variables for production: {', '.join(missing_vars)}"
            )

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DEBUG = True
    
    # Test SQL Server Database Configuration
    SQLSERVER_HOST = 'localhost'
    SQLSERVER_DATABASE = 'ABSENSI_TEST'
    SQLSERVER_USERNAME = 'sa'
    SQLSERVER_PASSWORD = 'Pkppastibisa-2025'
    SQLSERVER_DRIVER = 'ODBC Driver 17 for SQL Server'  # Use same as configured

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
