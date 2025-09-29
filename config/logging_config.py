"""
Logging configuration for the attendance system
Handles Unicode characters properly on Windows
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler


class SafeStreamHandler(logging.StreamHandler):
    """
    Safe stream handler that avoids encoding issues completely
    """
    def __init__(self, stream=None):
        if stream is None:
            stream = sys.stdout
        super().__init__(stream)
        
    def emit(self, record):
        try:
            msg = self.format(record)
            
            # Ensure we have a string
            if isinstance(msg, bytes):
                msg = msg.decode('utf-8', errors='replace')
            elif not isinstance(msg, str):
                msg = str(msg)
            
            # Use print instead of direct stream.write to avoid encoding issues
            print(msg, file=self.stream, flush=True)
            
        except Exception:
            # Use handleError to prevent infinite recursion
            self.handleError(record)


def setup_logging(name, log_level=logging.INFO, log_file=None):
    """
    Setup logging with Unicode support and conflict prevention
    
    Args:
        name: Logger name
        log_level: Logging level (default: INFO)
        log_file: Log file path (optional)
    
    Returns:
        logger: Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Always clear existing handlers to prevent conflicts
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()
    
    logger.setLevel(log_level)
    
    # Prevent propagation to root logger to avoid conflicts with Flask/werkzeug
    logger.propagate = False
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler with safe Unicode support
    console_handler = SafeStreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (if specified)
    if log_file:
        # Ensure log directory exists
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # Rotating file handler with UTF-8 encoding
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=3,
            encoding='utf-8',
            delay=True
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_worker_logger():
    """Get logger for attendance worker with optimized settings"""
    return setup_logging(
        'AttendanceWorker',
        log_level=logging.INFO,
        log_file='logs/attendance_worker.log'
    )


def get_streaming_logger():
    """Get logger for streaming service with optimized settings"""
    return setup_logging(
        'StreamingService',
        log_level=logging.INFO,
        log_file='logs/streaming_service.log'
    )


def get_app_logger():
    """Get logger for main application"""
    return setup_logging(
        'AttendanceApp',
        log_level=logging.INFO,
        log_file='logs/attendance_app.log'
    )


def get_background_logger(name, log_file=None):
    """Get optimized logger for background processes"""
    return setup_logging(
        name,
        log_level=logging.INFO,
        log_file=log_file
    )


def disable_other_loggers():
    """Disable problematic loggers that might cause conflicts"""
    # Disable werkzeug logging to prevent conflicts
    werkzeug_logger = logging.getLogger('werkzeug')
    werkzeug_logger.setLevel(logging.ERROR)
    werkzeug_logger.propagate = False
    
    # Set root logger to a higher level to prevent interference
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.WARNING)
