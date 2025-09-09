"""
Logging configuration for the attendance system
Handles Unicode characters properly on Windows
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler


class UnicodeStreamHandler(logging.StreamHandler):
    """
    Custom stream handler that properly handles Unicode on Windows
    """
    def __init__(self, stream=None):
        super().__init__(stream)
        
    def emit(self, record):
        try:
            msg = self.format(record)
            stream = self.stream
            
            # Handle Windows console encoding issues
            if hasattr(stream, 'encoding') and stream.encoding:
                # Try to encode with the stream's encoding
                try:
                    msg.encode(stream.encoding)
                except UnicodeEncodeError:
                    # Replace problematic characters with ASCII equivalents
                    msg = self._replace_unicode_chars(msg)
            
            stream.write(msg + self.terminator)
            self.flush()
            
        except Exception:
            self.handleError(record)
    
    def _replace_unicode_chars(self, text):
        """Replace Unicode emojis with ASCII equivalents"""
        replacements = {
            '🛑': '[STOP]',
            '📅': '[DATE]',
            '🔄': '[PROC]',
            '✅': '[OK]',
            '❌': '[ERR]',
            '⚠️': '[WARN]',
            '🚀': '[START]',
            '💾': '[SAVE]',
            '🔍': '[SEARCH]',
            '📊': '[STATS]',
            '🏃': '[RUN]',
            '⏰': '[TIME]',
            '📝': '[LOG]',
            '🔧': '[CONFIG]',
            '💡': '[INFO]',
            '🎯': '[TARGET]'
        }
        
        for unicode_char, ascii_replacement in replacements.items():
            text = text.replace(unicode_char, ascii_replacement)
        
        return text


def setup_logging(name, log_level=logging.INFO, log_file=None):
    """
    Setup logging with Unicode support
    
    Args:
        name: Logger name
        log_level: Logging level (default: INFO)
        log_file: Log file path (optional)
    
    Returns:
        logger: Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Prevent duplicate handlers
    if logger.handlers:
        return logger
    
    logger.setLevel(log_level)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler with Unicode support
    console_handler = UnicodeStreamHandler(sys.stdout)
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
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_worker_logger():
    """Get logger for attendance worker"""
    return setup_logging(
        'AttendanceWorker',
        log_file='logs/attendance_worker.log'
    )


def get_streaming_logger():
    """Get logger for streaming service"""
    return setup_logging(
        'StreamingService',
        log_file='logs/streaming_service.log'
    )


def get_app_logger():
    """Get logger for main application"""
    return setup_logging(
        'AttendanceApp',
        log_file='logs/app.log'
    )
