from datetime import datetime
from flask import (
    Blueprint, render_template, request, redirect, url_for,
    session, flash, abort,
)
from db import get_db_connection
from decorators import login_required, student_required
from utils import (
    allowed_submission, save_submission_file,
    activate_scheduled_exams, parse_exam_times, student_can_access_exam,
)

student_bp = Blueprint('student', __name__)


@student_bp.route('/student', endpoint='student_dashboard')
@login_required
@student_required
def student_dashboard():
    conn = get_db_connection()
    activate_scheduled_exams(conn)

    exams = conn.execute('''
        SELECT e.*, c.title AS course_title, c.code AS course_code
        FROM exams e
        LEFT JOIN courses c ON c.id = e.course_id
        WHERE e.course_id IS NULL
           OR EXISTS (
               SELECT 1 FROM enrollments en
               WHERE en.course_id = e.course_id AND en.student_id = ?
           )
        ORDER BY e.exam_date DESC
    ''', (session['user_id'],)).fetchall()

    subs = conn.execute(
        'SELECT exam_id, grade, feedback, submitted_at FROM submissions WHERE student_id = ?',
        (session['user_id'],),
    ).fetchall()
    results = {
        s['exam_id']: {
            'grade': s['grade'],
            'feedback': s['feedback'],
            'submitted_at': s['submitted_at'],
            'graded': s['grade'] is not None,
        }
        for s in subs
    }

    now = datetime.now()
    exams_prepared = []
    for e in exams:
        exam_dict = dict(e)
        timing = parse_exam_times(exam_dict, now)
        exam_dict.update(timing)
        exam_dict['student_submitted'] = e['id'] in results
        exams_prepared.append(exam_dict)

    conn.close()
    return render_template('student_dashboard.html', exams=exams_prepared, results=results)


@student_bp.route('/student/exam/<int:exam_id>/result', endpoint='exam_result')
@login_required
@student_required
def exam_result(exam_id):
    conn = get_db_connection()
    exam = conn.execute('''
        SELECT e.*, c.title AS course_title, c.code AS course_code
        FROM exams e
        LEFT JOIN courses c ON c.id = e.course_id
        WHERE e.id = ?
    ''', (exam_id,)).fetchone()

    if not exam or not student_can_access_exam(conn, session['user_id'], exam):
        conn.close()
        abort(404)

    submission = conn.execute(
        'SELECT * FROM submissions WHERE exam_id = ? AND student_id = ?',
        (exam_id, session['user_id']),
    ).fetchone()
    conn.close()

    if not submission:
        flash('You have not submitted this exam yet.', 'warning')
        return redirect(url_for('student.student_dashboard'))

    return render_template('student_result.html', exam=exam, submission=submission)


@student_bp.route('/submit_exam/<int:exam_id>', methods=['GET', 'POST'], endpoint='submit_exam')
@login_required
@student_required
def submit_exam(exam_id):
    conn = get_db_connection()
    activate_scheduled_exams(conn)
    exam = conn.execute('SELECT * FROM exams WHERE id = ?', (exam_id,)).fetchone()

    if not exam or not student_can_access_exam(conn, session['user_id'], exam):
        flash('Exam not found', 'danger')
        conn.close()
        return redirect(url_for('student.student_dashboard'))

    now = datetime.now()
    timing = parse_exam_times(dict(exam), now)

    if not timing['has_started']:
        flash('You cannot enter before the exam starts', 'danger')
        conn.close()
        return redirect(url_for('student.student_dashboard'))

    if not timing['can_submit']:
        flash('Exam time is over', 'danger')
        conn.close()
        return redirect(url_for('student.student_dashboard'))

    start_time = timing['start_dt']
    questions = conn.execute('SELECT * FROM questions WHERE exam_id = ?', (exam_id,)).fetchall()
    submission = conn.execute(
        'SELECT * FROM submissions WHERE exam_id = ? AND student_id = ?',
        (exam_id, session['user_id']),
    ).fetchone()

    if request.method == 'POST':
        if submission:
            flash('You have already submitted.', 'warning')
            conn.close()
            return redirect(url_for('student.student_dashboard'))

        if 'submission_file' not in request.files:
            flash('Please select a file.', 'danger')
            conn.close()
            return redirect(request.url)

        file = request.files['submission_file']
        if file.filename == '':
            flash('No file selected.', 'danger')
            conn.close()
            return redirect(request.url)

        if not allowed_submission(file.filename, exam['allowed_extensions']):
            allowed = exam['allowed_extensions'] or 'any'
            flash(f'File type not allowed. Allowed extensions: {allowed}', 'danger')
            conn.close()
            return redirect(request.url)

        filename = save_submission_file(file, session['user_id'], exam_id)
        if not filename:
            flash('Invalid file name.', 'danger')
            conn.close()
            return redirect(request.url)

        conn.execute(
            'INSERT INTO submissions (student_id, exam_id, file_path, submitted_at) VALUES (?, ?, ?, ?)',
            (session['user_id'], exam_id, filename, datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
        )
        conn.commit()
        conn.close()
        return redirect(url_for('student.submit_exam', exam_id=exam_id))

    conn.close()
    return render_template(
        'submit_exam.html',
        exam=exam,
        questions=questions,
        has_submitted=bool(submission),
        start_time=start_time,
        duration=exam['duration_minutes'],
    )


@student_bp.route('/student/<int:exam_id>/withdraw', methods=['POST'], endpoint='withdraw_submission')
@login_required
@student_required
def withdraw_submission(exam_id):
    conn = get_db_connection()
    exam = conn.execute('SELECT * FROM exams WHERE id = ?', (exam_id,)).fetchone()
    if not exam or not student_can_access_exam(conn, session['user_id'], exam):
        conn.close()
        flash('Exam not found', 'danger')
        return redirect(url_for('student.student_dashboard'))

    timing = parse_exam_times(dict(exam))
    if not timing['can_submit']:
        conn.close()
        flash('Cannot withdraw after exam has ended.', 'danger')
        return redirect(url_for('student.student_dashboard'))

    conn.execute(
        'DELETE FROM submissions WHERE student_id = ? AND exam_id = ?',
        (session['user_id'], exam_id),
    )
    conn.commit()
    conn.close()
    flash('Submission withdrawn. You can upload a new file.', 'info')
    return redirect(url_for('student.submit_exam', exam_id=exam_id))
