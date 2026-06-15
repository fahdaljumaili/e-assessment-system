from flask import Blueprint, render_template, request, redirect, url_for, session
from werkzeug.security import check_password_hash
from db import get_db_connection
from decorators import login_required

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/')
def home():
    return redirect(url_for('auth.login'))


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            return redirect(url_for('auth.dashboard'))
        error = 'Invalid username or password.'
    return render_template('login.html', error=error)


@auth_bp.route('/dashboard')
@login_required
def dashboard():
    if session['role'] == 'student':
        return redirect(url_for('student.student_dashboard'))
    if session['role'] == 'admin':
        return redirect(url_for('admin.admin_dashboard'))
    return redirect(url_for('instructor.instructor_dashboard'))


@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))
