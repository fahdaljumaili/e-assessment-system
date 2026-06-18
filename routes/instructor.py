import os
from datetime import datetime, timedelta
from flask import (
    Blueprint, render_template, request, redirect, url_for,
    session, flash, abort, send_file
)
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from werkzeug.exceptions import BadRequestKeyError
import config
from db import get_db_connection
from decorators import login_required, instructor_required
from utils import allowed_submission, save_question_image, save_submission_file, activate_scheduled_exams, parse_exam_times
from mcq import enrich_questions, validate_mcq_form
import json

instructor_bp = Blueprint('instructor', __name__, url_prefix='/instructor')


def _owns_exam(conn, exam_id, user_id):
    exam = conn.execute('SELECT * FROM exams WHERE id = ?', (exam_id,)).fetchone()
    if not exam:
        return None
    if int(exam['created_by']) != int(user_id):
        abort(403)
    return exam


@instructor_bp.route('', endpoint='instructor_dashboard')
@login_required
@instructor_required
def instructor_dashboard():
    conn = get_db_connection()
    activate_scheduled_exams(conn)
    rows = conn.execute('''
        SELECT e.*, c.title AS course_title, c.code AS course_code
        FROM exams e
        LEFT JOIN courses c ON c.id = e.course_id
        WHERE e.created_by = ?
        ORDER BY e.exam_date DESC
    ''', (session['user_id'],)).fetchall()
    exams_with_count = []
    now = datetime.now()

    for r in rows:
        exam = dict(r)
        count = conn.execute(
            'SELECT COUNT(*) FROM submissions WHERE exam_id = ?', (exam['id'],)
        ).fetchone()[0]
        exam['submission_count'] = count

        timing = parse_exam_times(exam, now)
        submissions_open = int(exam.get('submissions_open') or 0)
        is_active = submissions_open == 1 and timing['start_dt'] is not None and not timing['is_finished']

        exam.update({
            'start_dt': timing['start_dt'],
            'end_dt': timing['end_dt'],
            'is_finished': timing['is_finished'],
            'is_active': is_active,
            'is_scheduled_pending': timing['is_scheduled_pending'],
        })
        exams_with_count.append(exam)

    conn.close()
    return render_template('instructor_dashboard.html', exams=exams_with_count)


@instructor_bp.route('/<int:exam_id>/start', methods=['POST'], endpoint='start_exam')
@login_required
@instructor_required
def start_exam(exam_id):
    conn = get_db_connection()
    _owns_exam(conn, exam_id, session['user_id'])
    try:
        duration = int(request.form['duration_minutes'])
        if duration <= 0:
            flash('Exam duration must be greater than zero.', 'danger')
            conn.close()
            return redirect(url_for('instructor.instructor_dashboard'))
    except (KeyError, ValueError):
        flash('Invalid exam duration.', 'danger')
        conn.close()
        return redirect(url_for('instructor.instructor_dashboard'))

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn.execute(
        'UPDATE exams SET start_time = ?, duration_minutes = ?, submissions_open = 1 WHERE id = ?',
        (now, duration, exam_id),
    )
    conn.commit()
    conn.close()
    flash(f'Exam started for {duration} minutes.', 'success')
    return redirect(url_for('instructor.instructor_dashboard'))


@instructor_bp.route('/<int:exam_id>/finish', methods=['POST'], endpoint='finish_exam')
@login_required
@instructor_required
def finish_exam(exam_id):
    conn = get_db_connection()
    _owns_exam(conn, exam_id, session['user_id'])
    conn.execute(
        'UPDATE exams SET start_time = NULL, duration_minutes = 0, submissions_open = 0 WHERE id = ?',
        (exam_id,),
    )
    conn.commit()
    conn.close()
    flash('Exam has been finished and submissions are closed.', 'info')
    return redirect(url_for('instructor.instructor_dashboard'))


@instructor_bp.route('/create_exam', methods=['GET', 'POST'], endpoint='create_exam')
@login_required
@instructor_required
def create_exam():
    conn = get_db_connection()
    courses = conn.execute(
        'SELECT id, title, code FROM courses WHERE instructor_id = ? ORDER BY title',
        (session['user_id'],),
    ).fetchall()

    if request.method == 'POST':
        title = request.form['title']
        total_score = int(request.form['total_score'])
        exam_date = request.form['exam_date']
        allowed_ext = request.form.get('allowed_extensions', '').replace(' ', '')
        course_id = request.form.get('course_id')
        scheduled_start = request.form.get('scheduled_start', '').strip()
        duration = int(request.form.get('duration_minutes') or 0)

        if not course_id:
            flash('Please select a course.', 'danger')
            conn.close()
            return redirect(url_for('instructor.create_exam'))

        course = conn.execute(
            'SELECT id FROM courses WHERE id = ? AND instructor_id = ?',
            (course_id, session['user_id']),
        ).fetchone()
        if not course:
            conn.close()
            flash('Invalid course.', 'danger')
            return redirect(url_for('instructor.create_exam'))

        scheduled_db = None
        if scheduled_start:
            try:
                scheduled_db = datetime.strptime(scheduled_start, '%Y-%m-%dT%H:%M').strftime('%Y-%m-%d %H:%M:%S')
            except ValueError:
                conn.close()
                flash('Invalid scheduled date/time.', 'danger')
                return redirect(url_for('instructor.create_exam'))
            if duration <= 0:
                conn.close()
                flash('Duration is required for scheduled exams.', 'danger')
                return redirect(url_for('instructor.create_exam'))

        conn.execute(
            '''INSERT INTO exams
               (title, created_by, total_score, exam_date, allowed_extensions, course_id, scheduled_start, duration_minutes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
            (title, session['user_id'], total_score, exam_date, allowed_ext, course_id, scheduled_db, duration),
        )
        conn.commit()
        conn.close()
        flash('Exam created successfully!', 'success')
        return redirect(url_for('instructor.instructor_dashboard'))

    conn.close()
    return render_template('create_exam.html', courses=courses)


@instructor_bp.route('/<int:exam_id>/add_questions', methods=['GET', 'POST'], endpoint='add_questions')
@login_required
@instructor_required
def add_questions(exam_id):
    mode = request.args.get('mode', 'manual')
    conn = get_db_connection()
    exam = _owns_exam(conn, exam_id, session['user_id'])
    if exam is None:
        conn.close()
        abort(404, description='Exam not found')

    if request.method == 'POST' and 'delete_id' in request.form:
        qid = int(request.form['delete_id'])
        row = conn.execute('SELECT question_image FROM questions WHERE id = ?', (qid,)).fetchone()
        if row and row['question_image']:
            try:
                os.remove(os.path.join(config.QUESTION_UPLOAD_DIR, row['question_image']))
            except OSError:
                pass
        conn.execute('DELETE FROM questions WHERE id = ?', (qid,))
        conn.commit()
        flash('Question deleted.', 'warning')
        conn.close()
        return redirect(url_for('instructor.add_questions', exam_id=exam_id, mode=mode))

    if request.method == 'POST' and request.form.get('question_type') == 'mcq':
        question_text = request.form.get('question_text', '').strip()
        manual_score = int(request.form.get('manual_score', 0) or 0)
        mcq_data, err = validate_mcq_form(request.form)
        if err:
            flash(err, 'danger')
            conn.close()
            return redirect(url_for('instructor.add_questions', exam_id=exam_id, mode=mode))
        if not question_text:
            flash('Question text is required.', 'danger')
            conn.close()
            return redirect(url_for('instructor.add_questions', exam_id=exam_id, mode=mode))

        conn.execute(
            '''INSERT INTO questions
               (exam_id, question_text, suggested_score, question_type, mcq_options, correct_option)
               VALUES (?, ?, ?, 'mcq', ?, ?)''',
            (
                exam_id, question_text, manual_score,
                json.dumps(mcq_data['options'], ensure_ascii=False),
                mcq_data['correct_option'],
            ),
        )
        conn.commit()
        flash('MCQ question added!', 'success')
        conn.close()
        return redirect(url_for('instructor.add_questions', exam_id=exam_id, mode=mode))

    if request.method == 'POST' and 'question_text' in request.form:
        question_text = request.form['question_text'].strip()
        manual_score = int(request.form.get('manual_score', 0) or 0)
        img_filename = None
        if 'question_image' in request.files:
            f = request.files['question_image']
            if f and f.filename:
                result = save_question_image(f)
                if result is False:
                    flash('Image extension not allowed. Use png/jpg/jpeg/gif/webp.', 'danger')
                    conn.close()
                    return redirect(url_for('instructor.add_questions', exam_id=exam_id, mode=mode))
                img_filename = result

        conn.execute(
            '''INSERT INTO questions
               (exam_id, question_text, suggested_score, question_image, question_type)
               VALUES (?, ?, ?, ?, 'file')''',
            (exam_id, question_text, manual_score, img_filename),
        )
        conn.commit()
        flash('Question added!', 'success')
        conn.close()
        return redirect(url_for('instructor.add_questions', exam_id=exam_id, mode=mode))

    questions = enrich_questions(conn.execute(
        'SELECT * FROM questions WHERE exam_id = ? ORDER BY id', (exam_id,)
    ).fetchall())
    conn.close()
    return render_template('add_questions.html', exam=exam, questions=questions, mode=mode)


@instructor_bp.route('/<int:exam_id>/submissions', endpoint='view_submissions')
@login_required
@instructor_required
def view_submissions(exam_id):
    conn = get_db_connection()
    exam = _owns_exam(conn, exam_id, session['user_id'])
    if exam is None:
        conn.close()
        abort(404)
    subs = conn.execute('''
        SELECT s.*, u.full_name, u.username, s.grade, s.feedback, s.mcq_score, s.file_path
        FROM submissions s
        JOIN users u ON s.student_id = u.id
        WHERE s.exam_id = ?
    ''', (exam_id,)).fetchall()
    has_mcq = conn.execute(
        "SELECT 1 FROM questions WHERE exam_id = ? AND question_type = 'mcq' LIMIT 1",
        (exam_id,),
    ).fetchone()
    conn.close()
    return render_template('view_submissions.html', exam=exam, submissions=subs, has_mcq=bool(has_mcq))


@instructor_bp.route('/submission/<int:sub_id>/grade', methods=['POST'], endpoint='grade_submission')
@login_required
@instructor_required
def grade_submission(sub_id):
    try:
        feedback = request.form.get('feedback', '').strip()
        grade_raw = request.form.get('grade')

        if grade_raw is None or grade_raw == '':
            flash('Grade value is missing.', 'danger')
            return redirect(request.referrer or url_for('instructor.instructor_dashboard'))

        try:
            grade = int(grade_raw)
        except ValueError:
            flash('Invalid grade value. Please enter an integer.', 'danger')
            return redirect(request.referrer or url_for('instructor.instructor_dashboard'))

        conn = get_db_connection()
        sub = conn.execute('SELECT * FROM submissions WHERE id = ?', (sub_id,)).fetchone()
        if not sub:
            conn.close()
            abort(404)
        _owns_exam(conn, sub['exam_id'], session['user_id'])

        conn.execute(
            'UPDATE submissions SET grade = ?, feedback = ? WHERE id = ?',
            (grade, feedback, sub_id),
        )
        conn.commit()
        conn.close()
        flash('Grade saved successfully!', 'success')
        return redirect(request.referrer or url_for('instructor.instructor_dashboard'))

    except BadRequestKeyError as e:
        flash(f'Invalid request: missing field ({e}).', 'danger')
        return redirect(request.referrer or url_for('instructor.instructor_dashboard'))
    except Exception as e:
        flash(f'Error occurred: {str(e)}', 'danger')
        return redirect(request.referrer or url_for('instructor.instructor_dashboard'))


@instructor_bp.route('/<int:exam_id>/export_grades_pdf', endpoint='export_grades_pdf')
@login_required
@instructor_required
def export_grades_pdf(exam_id):
    conn = get_db_connection()
    exam = _owns_exam(conn, exam_id, session['user_id'])
    if exam is None:
        conn.close()
        abort(404)
    submissions = conn.execute('''
        SELECT users.username, submissions.grade
        FROM submissions
        JOIN users ON users.id = submissions.student_id
        WHERE submissions.exam_id = ?
    ''', (exam_id,)).fetchall()
    conn.close()

    pdf_path = os.path.join(config.UPLOAD_FOLDER, f'grades_exam_{exam_id}.pdf')
    c = canvas.Canvas(pdf_path, pagesize=letter)
    c.setFont('Helvetica-Bold', 16)
    c.drawString(200, 750, f'Grades Report - {exam["title"]}')

    c.setFont('Helvetica', 12)
    y = 700
    c.drawString(50, y, 'Username')
    c.drawString(300, y, 'Grade')
    c.line(50, y - 5, 550, y - 5)
    y -= 20

    for row in submissions:
        c.drawString(50, y, str(row['username']))
        c.drawString(300, y, str(row['grade']) if row['grade'] is not None else 'Not Graded')
        y -= 20
        if y < 50:
            c.showPage()
            c.setFont('Helvetica', 12)
            y = 750

    c.save()
    return send_file(pdf_path, as_attachment=True)


@instructor_bp.route('/<int:exam_id>/delete', methods=['POST'], endpoint='delete_exam')
@login_required
@instructor_required
def delete_exam(exam_id):
    conn = get_db_connection()
    try:
        exam = _owns_exam(conn, exam_id, session['user_id'])
        if exam is None:
            flash('Exam not found.', 'warning')
            return redirect(url_for('instructor.instructor_dashboard'))

        conn.execute('DELETE FROM submissions WHERE exam_id = ?', (exam_id,))
        conn.execute('DELETE FROM questions WHERE exam_id = ?', (exam_id,))
        conn.execute('DELETE FROM exams WHERE id = ?', (exam_id,))
        conn.commit()
    finally:
        conn.close()

    flash('Exam and all related data have been deleted.', 'success')
    return redirect(url_for('instructor.instructor_dashboard'))
