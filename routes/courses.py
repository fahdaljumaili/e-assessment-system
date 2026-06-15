import csv
import io
from flask import (
    Blueprint, render_template, request, redirect, url_for,
    session, flash, abort,
)
from werkzeug.security import generate_password_hash
from db import get_db_connection
from decorators import login_required, instructor_required

courses_bp = Blueprint('courses', __name__, url_prefix='/instructor/courses')


def _owns_course(conn, course_id, user_id):
    course = conn.execute('SELECT * FROM courses WHERE id = ?', (course_id,)).fetchone()
    if not course:
        return None
    if int(course['instructor_id']) != int(user_id):
        abort(403)
    return course


@courses_bp.route('')
@login_required
@instructor_required
def list_courses():
    conn = get_db_connection()
    courses = conn.execute('''
        SELECT c.*,
               (SELECT COUNT(*) FROM enrollments e WHERE e.course_id = c.id) AS student_count,
               (SELECT COUNT(*) FROM exams ex WHERE ex.course_id = c.id) AS exam_count
        FROM courses c
        WHERE c.instructor_id = ?
        ORDER BY c.title
    ''', (session['user_id'],)).fetchall()
    conn.close()
    return render_template('instructor_courses.html', courses=courses)


@courses_bp.route('/create', methods=['GET', 'POST'])
@login_required
@instructor_required
def create_course():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        code = request.form.get('code', '').strip().upper()
        if not title or not code:
            flash('Course title and code are required.', 'danger')
            return redirect(url_for('courses.create_course'))

        conn = get_db_connection()
        dup = conn.execute(
            'SELECT id FROM courses WHERE code = ? AND instructor_id = ?',
            (code, session['user_id']),
        ).fetchone()
        if dup:
            conn.close()
            flash('You already have a course with this code.', 'danger')
            return redirect(url_for('courses.create_course'))

        conn.execute(
            'INSERT INTO courses (title, code, instructor_id) VALUES (?, ?, ?)',
            (title, code, session['user_id']),
        )
        conn.commit()
        conn.close()
        flash(f'Course "{title}" created.', 'success')
        return redirect(url_for('courses.list_courses'))

    return render_template('create_course.html')


@courses_bp.route('/<int:course_id>')
@login_required
@instructor_required
def course_detail(course_id):
    conn = get_db_connection()
    course = _owns_course(conn, course_id, session['user_id'])
    if not course:
        conn.close()
        abort(404)

    students = conn.execute('''
        SELECT u.id, u.username, u.full_name, en.enrolled_at
        FROM enrollments en
        JOIN users u ON u.id = en.student_id
        WHERE en.course_id = ?
        ORDER BY u.username
    ''', (course_id,)).fetchall()

    exams = conn.execute(
        'SELECT id, title, exam_date, submissions_open FROM exams WHERE course_id = ? ORDER BY exam_date DESC',
        (course_id,),
    ).fetchall()

    all_students = conn.execute(
        "SELECT id, username, full_name FROM users WHERE role = 'student' ORDER BY username"
    ).fetchall()

    conn.close()
    return render_template(
        'course_detail.html',
        course=course,
        students=students,
        exams=exams,
        all_students=all_students,
    )


@courses_bp.route('/<int:course_id>/enroll', methods=['POST'])
@login_required
@instructor_required
def enroll_student(course_id):
    conn = get_db_connection()
    _owns_course(conn, course_id, session['user_id'])
    student_id = request.form.get('student_id')
    if not student_id:
        conn.close()
        flash('Select a student to enroll.', 'danger')
        return redirect(url_for('courses.course_detail', course_id=course_id))

    student = conn.execute(
        "SELECT id FROM users WHERE id = ? AND role = 'student'", (student_id,)
    ).fetchone()
    if not student:
        conn.close()
        flash('Invalid student.', 'danger')
        return redirect(url_for('courses.course_detail', course_id=course_id))

    conn.execute(
        'INSERT OR IGNORE INTO enrollments (course_id, student_id) VALUES (?, ?)',
        (course_id, student_id),
    )
    conn.commit()
    conn.close()
    flash('Student enrolled.', 'success')
    return redirect(url_for('courses.course_detail', course_id=course_id))


@courses_bp.route('/<int:course_id>/unenroll/<int:student_id>', methods=['POST'])
@login_required
@instructor_required
def unenroll_student(course_id, student_id):
    conn = get_db_connection()
    _owns_course(conn, course_id, session['user_id'])
    conn.execute(
        'DELETE FROM enrollments WHERE course_id = ? AND student_id = ?',
        (course_id, student_id),
    )
    conn.commit()
    conn.close()
    flash('Student removed from course.', 'info')
    return redirect(url_for('courses.course_detail', course_id=course_id))


@courses_bp.route('/<int:course_id>/import', methods=['POST'])
@login_required
@instructor_required
def import_students(course_id):
    conn = get_db_connection()
    _owns_course(conn, course_id, session['user_id'])

    file = request.files.get('csv_file')
    default_password = request.form.get('default_password', '1234').strip() or '1234'
    if not file or file.filename == '':
        conn.close()
        flash('Please select a CSV file.', 'danger')
        return redirect(url_for('courses.course_detail', course_id=course_id))

    try:
        text = file.read().decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames or 'username' not in [h.strip().lower() for h in reader.fieldnames]:
            conn.close()
            flash('CSV must include a "username" column.', 'danger')
            return redirect(url_for('courses.course_detail', course_id=course_id))

        created = enrolled = skipped = 0
        for row in reader:
            normalized = {k.strip().lower(): (v or '').strip() for k, v in row.items()}
            username = normalized.get('username', '')
            if not username:
                skipped += 1
                continue

            full_name = normalized.get('full_name') or None
            password = normalized.get('password') or default_password

            user = conn.execute('SELECT id, role FROM users WHERE username = ?', (username,)).fetchone()
            if user:
                if user['role'] != 'student':
                    skipped += 1
                    continue
                student_id = user['id']
            else:
                conn.execute(
                    'INSERT INTO users (username, password_hash, role, full_name) VALUES (?, ?, ?, ?)',
                    (username, generate_password_hash(password), 'student', full_name),
                )
                student_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
                created += 1

            before = conn.total_changes
            conn.execute(
                'INSERT OR IGNORE INTO enrollments (course_id, student_id) VALUES (?, ?)',
                (course_id, student_id),
            )
            if conn.total_changes > before:
                enrolled += 1

        conn.commit()
        conn.close()
        flash(f'Import done: {created} created, {enrolled} enrolled, {skipped} skipped.', 'success')
    except Exception as e:
        conn.close()
        flash(f'Import failed: {e}', 'danger')

    return redirect(url_for('courses.course_detail', course_id=course_id))
