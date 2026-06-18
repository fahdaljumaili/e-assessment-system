import os
from flask import Blueprint, send_from_directory, abort
from flask import session
import config
from decorators import login_required
from file_access import can_access_submission_file, can_access_question_image

files_bp = Blueprint('files', __name__)


@files_bp.route('/submissions/<path:filename>', endpoint='download_submission')
@login_required
def download_submission(filename):
    allowed, safe_name = can_access_submission_file(
        session['user_id'], session['role'], filename
    )
    if not allowed:
        abort(403)
    return send_from_directory(config.UPLOAD_FOLDER, safe_name)


@files_bp.route('/question-images/<path:filename>', endpoint='question_image')
@login_required
def question_image(filename):
    allowed, safe_name = can_access_question_image(
        session['user_id'], session['role'], filename
    )
    if not allowed:
        abort(403)
    return send_from_directory(config.QUESTION_UPLOAD_DIR, safe_name)
