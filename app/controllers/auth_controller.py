"""
Authentication Controller
Handles user login, logout, and session management
"""
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from functools import wraps
from app.models.user import User
import logging

logger = logging.getLogger(__name__)

# Create Blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

def login_required(f):
    """Decorator to protect routes that require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Silakan login terlebih dahulu untuk mengakses halaman ini.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def get_current_user():
    """Get current logged in user from session"""
    if 'user_id' in session:
        return User.find_by_id(session['user_id'])
    return None

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login page and handler"""
    # If already logged in, redirect to home
    if 'user_id' in session:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        
        if not email or not password:
            flash('Email dan password harus diisi!', 'danger')
            return render_template('auth/login.html')
        
        # Find user by email
        user = User.find_by_email(email)
        
        if user and user.check_password(password):
            if not user.is_active():
                flash('Akun Anda tidak aktif. Hubungi administrator.', 'danger')
                return render_template('auth/login.html')
            
            # Store user info in session
            session['user_id'] = user.id
            session['user_email'] = user.email
            session['user_name'] = user.name
            session['user_role'] = user.role
            session['user_pin'] = user.pin
            
            logger.info(f"[OK] User logged in: {user.email} (role: {user.role})")
            
            # Redirect to next page or home
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('main.index'))
        else:
            flash('Email atau password salah!', 'danger')
            logger.warning(f"[WARN] Failed login attempt: {email}")
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
def logout():
    """Logout handler"""
    user_email = session.get('user_email', 'Unknown')
    session.clear()
    flash('Anda telah logout.', 'success')
    logger.info(f"[OK] User logged out: {user_email}")
    return redirect(url_for('auth.login'))

@auth_bp.route('/check-session')
def check_session():
    """API endpoint to check if user is logged in"""
    if 'user_id' in session:
        user = get_current_user()
        if user:
            return jsonify({
                'logged_in': True,
                'user': user.to_dict()
            })
    
    return jsonify({'logged_in': False}), 401
