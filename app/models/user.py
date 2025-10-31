"""
User Model
Handles user authentication and management
"""
from werkzeug.security import generate_password_hash, check_password_hash
from config.database import db_manager
import pyodbc
import logging

logger = logging.getLogger(__name__)

class User:
    """User model for authentication"""
    
    def __init__(self, id=None, email=None, password=None, name=None, status='aktif', role=None, pin=None):
        self.id = id
        self.email = email
        self.password = password  # This is password hash
        self.name = name
        self.status = status
        self.role = role
        self.pin = pin
    
    @staticmethod
    def create_table():
        """Create users table if not exists"""
        try:
            connection = db_manager.get_connection()
            cursor = connection.cursor()
            
            cursor.execute("""
                IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='users' AND xtype='U')
                BEGIN
                    CREATE TABLE users (
                        id BIGINT IDENTITY(1,1) NOT NULL,
                        name NVARCHAR(255) COLLATE Latin1_General_CI_AS NOT NULL,
                        email NVARCHAR(255) COLLATE Latin1_General_CI_AS NOT NULL,
                        email_verified_at DATETIME NULL,
                        password NVARCHAR(255) COLLATE Latin1_General_CI_AS NOT NULL,
                        remember_token NVARCHAR(100) COLLATE Latin1_General_CI_AS NULL,
                        created_at DATETIME NULL,
                        updated_at DATETIME NULL,
                        status NVARCHAR(255) COLLATE Latin1_General_CI_AS DEFAULT 'aktif' NOT NULL,
                        [role] NVARCHAR(255) COLLATE Latin1_General_CI_AS NULL,
                        pin NVARCHAR(255) COLLATE Latin1_General_CI_AS NULL,
                        CONSTRAINT PK__users__3213E83F99303A5E PRIMARY KEY (id)
                    );
                    
                    CREATE UNIQUE NONCLUSTERED INDEX users_email_unique 
                    ON users (email ASC)  
                    WITH (PAD_INDEX = OFF, FILLFACTOR = 100, SORT_IN_TEMPDB = OFF, 
                          IGNORE_DUP_KEY = OFF, STATISTICS_NORECOMPUTE = OFF, 
                          ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON)
                    ON [PRIMARY];
                END
            """)
            connection.commit()
            logger.info("[OK] Users table checked/created successfully")
            return True
        except Exception as e:
            logger.error(f"[ERROR] Failed to create users table: {str(e)}")
            return False
        finally:
            if connection:
                connection.close()
    
    @staticmethod
    def create_default_user():
        """Create default admin user if no users exist"""
        try:
            connection = db_manager.get_connection()
            cursor = connection.cursor()
            
            # Check if any users exist
            cursor.execute("SELECT COUNT(*) as count FROM users")
            result = cursor.fetchone()
            
            if result.count == 0:
                # Create default admin user
                default_email = "admin@absensi.com"
                default_password = "admin123"
                default_name = "Administrator"
                default_role = "admin"
                
                password_hash = generate_password_hash(default_password)
                
                cursor.execute("""
                    INSERT INTO users (name, email, password, status, [role], created_at, updated_at)
                    VALUES (?, ?, ?, 'aktif', ?, GETDATE(), GETDATE())
                """, (default_name, default_email, password_hash, default_role))
                
                connection.commit()
                logger.info(f"[OK] Default user created: {default_email} / {default_password}")
                return True
            else:
                logger.info("[INFO] Users already exist, skipping default user creation")
                return True
                
        except Exception as e:
            logger.error(f"[ERROR] Failed to create default user: {str(e)}")
            return False
        finally:
            if connection:
                connection.close()
    
    @staticmethod
    def find_by_email(email):
        """Find user by email"""
        try:
            connection = db_manager.get_connection()
            cursor = connection.cursor()
            
            cursor.execute("""
                SELECT id, email, password, name, status, [role], pin
                FROM users
                WHERE email = ?
            """, (email,))
            
            row = cursor.fetchone()
            
            if row:
                return User(
                    id=row.id,
                    email=row.email,
                    password=row.password,
                    name=row.name,
                    status=row.status,
                    role=row.role,
                    pin=row.pin
                )
            return None
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to find user by email: {str(e)}")
            return None
        finally:
            if connection:
                connection.close()
    
    @staticmethod
    def find_by_id(user_id):
        """Find user by ID"""
        try:
            connection = db_manager.get_connection()
            cursor = connection.cursor()
            
            cursor.execute("""
                SELECT id, email, password, name, status, [role], pin
                FROM users
                WHERE id = ?
            """, (user_id,))
            
            row = cursor.fetchone()
            
            if row:
                return User(
                    id=row.id,
                    email=row.email,
                    password=row.password,
                    name=row.name,
                    status=row.status,
                    role=row.role,
                    pin=row.pin
                )
            return None
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to find user by ID: {str(e)}")
            return None
        finally:
            if connection:
                connection.close()
    
    def check_password(self, password_input):
        """Verify password"""
        # Check if password hash is valid (starts with hash method identifier)
        if not self.password or not self.password.startswith(('pbkdf2:', 'scrypt:', 'bcrypt')):
            logger.warning(f"[WARN] Invalid password hash format for user: {self.email}")
            # Try direct comparison for legacy plain text passwords
            return self.password == password_input
        
        try:
            return check_password_hash(self.password, password_input)
        except ValueError as e:
            logger.error(f"[ERROR] Password hash verification failed for {self.email}: {e}")
            # Fallback: try plain text comparison
            return self.password == password_input
    
    def is_active(self):
        """Check if user is active"""
        return self.status == 'aktif'
    
    def is_admin(self):
        """Check if user has admin role"""
        return self.role == 'admin'
    
    @staticmethod
    def create_user(email, password_input, name, role='user', pin=None):
        """Create new user"""
        try:
            connection = db_manager.get_connection()
            cursor = connection.cursor()
            
            password_hash = generate_password_hash(password_input)
            
            cursor.execute("""
                INSERT INTO users (name, email, password, status, [role], pin, created_at, updated_at)
                VALUES (?, ?, ?, 'aktif', ?, ?, GETDATE(), GETDATE())
            """, (name, email, password_hash, role, pin))
            
            connection.commit()
            logger.info(f"[OK] User created: {email}")
            return True
            
        except pyodbc.IntegrityError:
            logger.error(f"[ERROR] User with email {email} already exists")
            return False
        except Exception as e:
            logger.error(f"[ERROR] Failed to create user: {str(e)}")
            return False
        finally:
            if connection:
                connection.close()
    
    def to_dict(self):
        """Convert user to dictionary (excluding password)"""
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'status': self.status,
            'role': self.role,
            'pin': self.pin
        }
