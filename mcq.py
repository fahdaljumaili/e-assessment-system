import json


MCQ_ONLY_FILE_PATH = '__mcq_only__'


def enrich_questions(rows):
    """Parse question rows for templates; attach `options` list for MCQ."""
    result = []
    for row in rows:
        q = dict(row)
        q['question_type'] = q.get('question_type') or 'file'
        if q['question_type'] == 'mcq' and q.get('mcq_options'):
            try:
                q['options'] = json.loads(q['mcq_options'])
            except (json.JSONDecodeError, TypeError):
                q['options'] = []
        else:
            q['options'] = []
        result.append(q)
    return result


def exam_has_file_questions(questions):
    return any((q.get('question_type') or 'file') == 'file' for q in questions)


def exam_has_mcq_questions(questions):
    return any(q.get('question_type') == 'mcq' for q in questions)


def parse_mcq_options_from_form(form):
    """Extract non-empty options from form fields option_0 .. option_5."""
    options = []
    for i in range(6):
        text = form.get(f'option_{i}', '').strip()
        if text:
            options.append(text)
    return options


def validate_mcq_form(form):
    options = parse_mcq_options_from_form(form)
    if len(options) < 2:
        return None, 'MCQ requires at least 2 options.'
    try:
        correct = int(form.get('correct_option', ''))
    except (TypeError, ValueError):
        return None, 'Select the correct answer.'
    if correct < 0 or correct >= len(options):
        return None, 'Invalid correct answer selection.'
    return {'options': options, 'correct_option': correct}, None


def grade_mcq_answers(conn, submission_id, exam_id, form):
    """Grade MCQ responses from form keys mcq_<question_id>. Returns total MCQ score."""
    questions = conn.execute(
        "SELECT * FROM questions WHERE exam_id = ? AND question_type = 'mcq'",
        (exam_id,),
    ).fetchall()
    total = 0
    for q in questions:
        raw = form.get(f'mcq_{q["id"]}')
        if raw is None or raw == '':
            conn.execute(
                '''INSERT INTO mcq_answers
                   (submission_id, question_id, selected_option, is_correct, points_earned)
                   VALUES (?, ?, NULL, 0, 0)''',
                (submission_id, q['id']),
            )
            continue
        try:
            selected = int(raw)
        except ValueError:
            selected = -1
        correct = int(q['correct_option'])
        is_correct = selected == correct
        points = int(q['suggested_score']) if is_correct else 0
        total += points
        conn.execute(
            '''INSERT INTO mcq_answers
               (submission_id, question_id, selected_option, is_correct, points_earned)
               VALUES (?, ?, ?, ?, ?)''',
            (submission_id, q['id'], selected, int(is_correct), points),
        )
    return total


def get_mcq_breakdown(conn, submission_id):
    """Return MCQ answer rows with question text for result views."""
    return conn.execute('''
        SELECT ma.*, q.question_text, q.mcq_options, q.correct_option, q.suggested_score
        FROM mcq_answers ma
        JOIN questions q ON q.id = ma.question_id
        WHERE ma.submission_id = ?
        ORDER BY q.id
    ''', (submission_id,)).fetchall()


def option_label(index):
    return chr(65 + index)  # A, B, C, ...
