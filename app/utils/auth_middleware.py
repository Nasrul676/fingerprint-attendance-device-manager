"""
Authentication Middleware
Provides centralized authentication checking
"""
from flask import session, redirect, url_for, request, flash
from functools import wraps

def login_required(f):
    """
    Decorator to protect routes that require authentication
    Usage: @login_required above any route function
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Silakan login terlebih dahulu untuk mengakses halaman ini.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def get_current_user():
    """Get current logged in user info from session"""
    if 'user_id' in session:
        return {
            'id': session.get('user_id'),
            'email': session.get('user_email'),
            'name': session.get('user_name')
        }
    return None
