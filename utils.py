import os
import time
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
import config


def exam_is_finished(exam):
    start_time = exam['start_time']
    duration = exam['duration_minutes']
    if not start_time or not duration:
        return False
    try:
        start_dt = datetime.strptime(str(start_time), '%Y-%m-%d %H:%M:%S')
        end_dt = start_dt + timedelta(minutes=int(duration))
        return datetime.now() > end_dt
    except Exception:
        return False


def allowed_image(filename):
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    return ext in config.ALLOWED_IMAGE_EXT


def allowed_submission(filename, allowed_extensions_str):
    if not allowed_extensions_str or not allowed_extensions_str.strip():
        return True
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    allowed = {
        e.strip().lower().lstrip('.')
        for e in allowed_extensions_str.split(',')
        if e.strip()
    }
    return ext in allowed


def save_question_image(file):
    if not file or not file.filename:
        return None
    if not allowed_image(file.filename):
        return False
    filename = secure_filename(file.filename)
    filename = f'{int(time.time())}_{filename}'
    dest = os.path.join(config.QUESTION_UPLOAD_DIR, filename)
    file.save(dest)
    return filename


def save_submission_file(file, user_id, exam_id):
    safe_name = secure_filename(file.filename)
    if not safe_name:
        return None
    filename = f'{user_id}_{exam_id}_{safe_name}'
    filepath = os.path.join(config.UPLOAD_FOLDER, filename)
    file.save(filepath)
    return filename


def activate_scheduled_exams(conn):
    """Open exams whose scheduled start time has arrived."""
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn.execute('''
        UPDATE exams
        SET start_time = scheduled_start, submissions_open = 1
        WHERE scheduled_start IS NOT NULL
          AND scheduled_start <= ?
          AND submissions_open = 0
          AND start_time IS NULL
          AND duration_minutes > 0
    ''', (now,))
    conn.commit()


def parse_exam_times(exam, now=None):
    """Return common exam timing fields for templates and access checks."""
    now = now or datetime.now()
    start_val = exam['start_time'] if exam['start_time'] else exam.get('scheduled_start')
    duration_val = exam['duration_minutes'] or 0
    submissions_open = int(exam.get('submissions_open') or 0)

    start_dt = None
    end_dt = None
    has_started = False
    can_submit = False
    is_scheduled_pending = False

    scheduled = exam.get('scheduled_start')
    if scheduled and not exam['start_time']:
        try:
            sched_dt = datetime.strptime(str(scheduled), '%Y-%m-%d %H:%M:%S')
            if now < sched_dt:
                is_scheduled_pending = True
        except Exception:
            pass

    if start_val and duration_val:
        try:
            start_dt = datetime.strptime(str(start_val), '%Y-%m-%d %H:%M:%S')
            end_dt = start_dt + timedelta(minutes=int(duration_val))
            has_started = now >= start_dt
            can_submit = has_started and now <= end_dt and submissions_open == 1
        except Exception:
            pass

    return {
        'start_dt': start_dt,
        'end_dt': end_dt,
        'has_started': has_started,
        'can_submit': can_submit,
        'is_scheduled_pending': is_scheduled_pending,
        'is_finished': bool(end_dt and now > end_dt),
    }


def student_can_access_exam(conn, student_id, exam):
    if not exam['course_id']:
        return True
    row = conn.execute(
        'SELECT 1 FROM enrollments WHERE course_id = ? AND student_id = ?',
        (exam['course_id'], student_id),
    ).fetchone()
    return row is not None
