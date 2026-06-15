from flask import Blueprint, render_template, request, redirect, url_for, session, flash, abort
from werkzeug.security import generate_password_hash
from db import get_db_connection
from decorators import login_required, admin_required

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

VALID_ROLES = ('student', 'instructor', 'admin')


@admin_bp.route('')
@login_required
@admin_required
def admin_dashboard():
    conn = get_db_connection()
    users = conn.execute(
        'SELECT id, username, full_name, role, created_at FROM users ORDER BY role, username'
    ).fetchall()
    conn.close()
    return render_template('admin_dashboard.html', users=users)


@admin_bp.route('/users/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_user():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        full_name = request.form.get('full_name', '').strip()
        role = request.form.get('role', '')

        if not username or not password:
            flash('Username and password are required.', 'danger')
            return redirect(url_for('admin.create_user'))

        if role not in VALID_ROLES:
            flash('Invalid role selected.', 'danger')
            return redirect(url_for('admin.create_user'))

        if len(password) < 4:
            flash('Password must be at least 4 characters.', 'danger')
            return redirect(url_for('admin.create_user'))

        conn = get_db_connection()
        existing = conn.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
        if existing:
            conn.close()
            flash('Username already exists.', 'danger')
            return redirect(url_for('admin.create_user'))

        conn.execute(
            'INSERT INTO users (username, password_hash, role, full_name) VALUES (?, ?, ?, ?)',
            (username, generate_password_hash(password), role, full_name or None),
        )
        conn.commit()
        conn.close()
        flash(f'User "{username}" created successfully.', 'success')
        return redirect(url_for('admin.admin_dashboard'))

    return render_template('create_user.html', roles=VALID_ROLES)


@admin_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    if not user:
        conn.close()
        abort(404)

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        full_name = request.form.get('full_name', '').strip()
        role = request.form.get('role', '')
        password = request.form.get('password', '')

        if not username:
            flash('Username is required.', 'danger')
            conn.close()
            return redirect(url_for('admin.edit_user', user_id=user_id))

        if role not in VALID_ROLES:
            flash('Invalid role selected.', 'danger')
            conn.close()
            return redirect(url_for('admin.edit_user', user_id=user_id))

        if user_id == session['user_id'] and role != 'admin':
            flash('You cannot remove your own admin role.', 'danger')
            conn.close()
            return redirect(url_for('admin.edit_user', user_id=user_id))

        duplicate = conn.execute(
            'SELECT id FROM users WHERE username = ? AND id != ?', (username, user_id)
        ).fetchone()
        if duplicate:
            conn.close()
            flash('Username already taken.', 'danger')
            return redirect(url_for('admin.edit_user', user_id=user_id))

        if password:
            if len(password) < 4:
                flash('Password must be at least 4 characters.', 'danger')
                conn.close()
                return redirect(url_for('admin.edit_user', user_id=user_id))
            conn.execute(
                'UPDATE users SET username = ?, full_name = ?, role = ?, password_hash = ? WHERE id = ?',
                (username, full_name or None, role, generate_password_hash(password), user_id),
            )
        else:
            conn.execute(
                'UPDATE users SET username = ?, full_name = ?, role = ? WHERE id = ?',
                (username, full_name or None, role, user_id),
            )

        conn.commit()
        conn.close()
        flash('User updated successfully.', 'success')
        return redirect(url_for('admin.admin_dashboard'))

    conn.close()
    return render_template('edit_user.html', user=user, roles=VALID_ROLES)


@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    if user_id == session['user_id']:
        flash('You cannot delete your own account.', 'danger')
        return redirect(url_for('admin.admin_dashboard'))

    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    if not user:
        conn.close()
        abort(404)

    conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()
    flash(f'User "{user["username"]}" deleted.', 'success')
    return redirect(url_for('admin.admin_dashboard'))
