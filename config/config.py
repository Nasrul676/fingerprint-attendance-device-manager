import os
import secrets
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

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    
    # SQL Server Database Configuration
    SQLSERVER_HOST = os.environ.get('SQLSERVER_HOST') or 'localhost'
    SQLSERVER_DATABASE = os.environ.get('SQLSERVER_DATABASE') or 'ABSENSI'
    SQLSERVER_USERNAME = os.environ.get('SQLSERVER_USERNAME') or 'sa'
    SQLSERVER_PASSWORD = os.environ.get('SQLSERVER_PASSWORD') or ''
    SQLSERVER_DRIVER = os.environ.get('SQLSERVER_DRIVER') or '{ODBC Driver 17 for SQL Server}'

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
    SQLSERVER_DRIVER = os.environ.get('SQLSERVER_DRIVER') or '{ODBC Driver 17 for SQL Server}'
    
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
    SQLSERVER_PASSWORD = ''
    SQLSERVER_DRIVER = '{ODBC Driver 17 for SQL Server}'

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
