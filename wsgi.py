#!/usr/bin/env python3
"""
WSGI configuration for Attendance System.
This file is used for production deployment with WSGI servers like Gunicorn.
"""

import os
import sys

# Add the project directory to Python path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

from app import create_app

# Create application instance for production
application = create_app('production')

if __name__ == "__main__":
    application.run()
