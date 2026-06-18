import os
import config
from db import get_db_connection
from utils import student_can_access_exam
from mcq import MCQ_ONLY_FILE_PATH


def _safe_basename(filename):
    """Reject path traversal; return basename only."""
    if not filename or '..' in filename or filename.startswith(('/', '\\')):
        return None
    safe = os.path.basename(filename.replace('\\', '/'))
    return safe or None


def can_access_submission_file(user_id, role, filename):
    """
    Check whether the logged-in user may download a file from submissions/.
    Returns (allowed: bool, safe_filename: str|None).
    """
    safe = _safe_basename(filename)
    if not safe:
        return False, None

    filepath = os.path.join(config.UPLOAD_FOLDER, safe)
    if not os.path.isfile(filepath):
        return False, None

    conn = get_db_connection()
    try:
        if safe.startswith('grades_exam_') and safe.endswith('.pdf'):
            try:
                exam_id = int(safe[len('grades_exam_'):-len('.pdf')])
            except ValueError:
                return False, None
            exam = conn.execute('SELECT created_by FROM exams WHERE id = ?', (exam_id,)).fetchone()
            if not exam:
                return False, None
            if role == 'admin':
                return True, safe
            if role == 'instructor' and int(exam['created_by']) == int(user_id):
                return True, safe
            return False, None

        row = conn.execute('''
            SELECT s.student_id, e.created_by, e.id AS exam_id, e.course_id
            FROM submissions s
            JOIN exams e ON e.id = s.exam_id
            WHERE s.file_path = ?
        ''', (safe,)).fetchone()
        if not row:
            return False, None

        if role == 'admin':
            return True, safe
        if role == 'instructor' and int(row['created_by']) == int(user_id):
            return True, safe
        if role == 'student' and int(row['student_id']) == int(user_id):
            return True, safe
        return False, None
    finally:
        conn.close()


def can_access_question_image(user_id, role, filename):
    """
    Check whether the logged-in user may view a question image.
    Returns (allowed: bool, safe_filename: str|None).
    """
    safe = _safe_basename(filename)
    if not safe:
        return False, None

    filepath = os.path.join(config.QUESTION_UPLOAD_DIR, safe)
    if not os.path.isfile(filepath):
        return False, None

    conn = get_db_connection()
    try:
        row = conn.execute('''
            SELECT e.id AS exam_id, e.created_by, e.course_id
            FROM questions q
            JOIN exams e ON e.id = q.exam_id
            WHERE q.question_image = ?
        ''', (safe,)).fetchone()
        if not row:
            return False, None

        if role == 'admin':
            return True, safe
        if role == 'instructor' and int(row['created_by']) == int(user_id):
            return True, safe
        if role == 'student':
            exam = {
                'course_id': row['course_id'],
                'id': row['exam_id'],
            }
            if student_can_access_exam(conn, user_id, exam):
                return True, safe
        return False, None
    finally:
        conn.close()
