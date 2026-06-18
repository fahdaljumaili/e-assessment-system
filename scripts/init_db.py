import os
import sys
import sqlite3
from werkzeug.security import generate_password_hash

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

DB_PATH = config.DATABASE


def _add_column(cur, table, column, col_type):
    cur.execute(f'PRAGMA table_info({table})')
    if column not in [row[1] for row in cur.fetchall()]:
        cur.execute(f'ALTER TABLE {table} ADD COLUMN {column} {col_type}')


def migrate_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute('''
    CREATE TABLE IF NOT EXISTS courses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        code TEXT NOT NULL,
        instructor_id INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (instructor_id) REFERENCES users(id),
        UNIQUE(code, instructor_id)
    )
    ''')

    cur.execute('''
    CREATE TABLE IF NOT EXISTS enrollments (
        course_id INTEGER NOT NULL,
        student_id INTEGER NOT NULL,
        enrolled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (course_id, student_id),
        FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
        FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE
    )
    ''')

    _add_column(cur, 'exams', 'course_id', 'INTEGER REFERENCES courses(id)')
    _add_column(cur, 'exams', 'scheduled_start', 'TEXT')

    _add_column(cur, 'questions', 'question_type', "TEXT NOT NULL DEFAULT 'file'")
    _add_column(cur, 'questions', 'mcq_options', 'TEXT')
    _add_column(cur, 'questions', 'correct_option', 'INTEGER')
    _add_column(cur, 'submissions', 'mcq_score', 'INTEGER DEFAULT 0')

    cur.execute('''
    CREATE TABLE IF NOT EXISTS mcq_answers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        submission_id INTEGER NOT NULL,
        question_id INTEGER NOT NULL,
        selected_option INTEGER,
        is_correct INTEGER NOT NULL DEFAULT 0,
        points_earned INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY (submission_id) REFERENCES submissions(id) ON DELETE CASCADE,
        FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE,
        UNIQUE(submission_id, question_id)
    )
    ''')

    # Demo course for existing installations
    instructor = cur.execute("SELECT id FROM users WHERE username = 'instructor1'").fetchone()
    student = cur.execute("SELECT id FROM users WHERE username = 'student1'").fetchone()
    if instructor and student and cur.execute('SELECT COUNT(*) FROM courses').fetchone()[0] == 0:
        cur.execute(
            "INSERT INTO courses (title, code, instructor_id) VALUES (?, ?, ?)",
            ('Introduction to Programming', 'CS101', instructor[0]),
        )
        course_id = cur.execute('SELECT last_insert_rowid()').fetchone()[0]
        cur.execute(
            'INSERT OR IGNORE INTO enrollments (course_id, student_id) VALUES (?, ?)',
            (course_id, student[0]),
        )

    conn.commit()
    conn.close()
    print('Database migration completed.')


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT CHECK(role IN ('student','instructor','admin')) NOT NULL,
        full_name TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    cur.execute('''
    CREATE TABLE IF NOT EXISTS courses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        code TEXT NOT NULL,
        instructor_id INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (instructor_id) REFERENCES users(id),
        UNIQUE(code, instructor_id)
    )
    ''')

    cur.execute('''
    CREATE TABLE IF NOT EXISTS enrollments (
        course_id INTEGER NOT NULL,
        student_id INTEGER NOT NULL,
        enrolled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (course_id, student_id),
        FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
        FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE
    )
    ''')

    cur.execute('''
    CREATE TABLE IF NOT EXISTS exams (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        start_time TEXT,
        exam_date TEXT,
        exam_datetime TEXT,
        created_by INTEGER NOT NULL,
        course_id INTEGER,
        scheduled_start TEXT,
        total_score INTEGER NOT NULL,
        duration_minutes INTEGER NOT NULL DEFAULT 0,
        allowed_extensions TEXT,
        submissions_open INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY (created_by) REFERENCES users(id),
        FOREIGN KEY (course_id) REFERENCES courses(id)
    )
    ''')

    cur.execute('''
    CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        image_path TEXT,
        question_image TEXT,
        exam_id INTEGER NOT NULL,
        question_text TEXT NOT NULL,
        question_type TEXT NOT NULL DEFAULT 'file',
        mcq_options TEXT,
        correct_option INTEGER,
        suggested_score INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY (exam_id) REFERENCES exams(id)
    )
    ''')

    cur.execute('''
    CREATE TABLE IF NOT EXISTS submissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        exam_id INTEGER NOT NULL,
        file_path TEXT NOT NULL,
        mcq_score INTEGER DEFAULT 0,
        grade INTEGER,
        feedback TEXT,
        submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES users(id),
        FOREIGN KEY (exam_id) REFERENCES exams(id)
    )
    ''')

    cur.execute('''
    CREATE TABLE IF NOT EXISTS mcq_answers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        submission_id INTEGER NOT NULL,
        question_id INTEGER NOT NULL,
        selected_option INTEGER,
        is_correct INTEGER NOT NULL DEFAULT 0,
        points_earned INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY (submission_id) REFERENCES submissions(id) ON DELETE CASCADE,
        FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE,
        UNIQUE(submission_id, question_id)
    )
    ''')

    cur.execute(
        "INSERT OR IGNORE INTO users (username, password_hash, role, full_name) VALUES (?, ?, ?, ?)",
        ('student1', generate_password_hash('1234'), 'student', 'Student 1'),
    )
    cur.execute(
        "INSERT OR IGNORE INTO users (username, password_hash, role, full_name) VALUES (?, ?, ?, ?)",
        ('instructor1', generate_password_hash('1234'), 'instructor', 'Instructor 1'),
    )
    cur.execute(
        "INSERT OR IGNORE INTO users (username, password_hash, role, full_name) VALUES (?, ?, ?, ?)",
        ('admin1', generate_password_hash('admin123'), 'admin', 'Administrator'),
    )

    instructor = cur.execute("SELECT id FROM users WHERE username = 'instructor1'").fetchone()
    student = cur.execute("SELECT id FROM users WHERE username = 'student1'").fetchone()
    if instructor and student:
        cur.execute(
            "INSERT OR IGNORE INTO courses (title, code, instructor_id) VALUES (?, ?, ?)",
            ('Introduction to Programming', 'CS101', instructor[0]),
        )
        course = cur.execute(
            "SELECT id FROM courses WHERE code = 'CS101' AND instructor_id = ?",
            (instructor[0],),
        ).fetchone()
        if course:
            cur.execute(
                'INSERT OR IGNORE INTO enrollments (course_id, student_id) VALUES (?, ?)',
                (course[0], student[0]),
            )

    conn.commit()
    conn.close()
    migrate_db()
    print('Database initialized successfully.')


if __name__ == '__main__':
    init_db()
