
#!/usr/bin/env python3
"""
Development entry point for the Attendance System Flask application.
For production, use wsgi.py instead.
"""

import os
from app import create_app

# Create Flask application instance
env = os.environ.get('FLASK_ENV', 'development')
app = create_app(env)

if __name__ == '__main__':
    # Warning for production usage
    if env == 'production':
        print("⚠️  WARNING: Running in production mode with development server!")
        print("   For production, use a WSGI server like Gunicorn instead.")
        print("   Example: gunicorn -w 4 -b 127.0.0.1:5000 wsgi:application")
        print("=" * 60)
    
    # Get configuration from environment
    host = os.environ.get('FLASK_HOST', '127.0.0.1')
    port = int(os.environ.get('FLASK_PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    app.run(host=host, port=port, debug=debug)