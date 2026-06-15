import os

SECRET_KEY = os.getenv('SECRET_KEY', 'replace_with_secure_random_string')

DATABASE = 'db.sqlite3'
UPLOAD_FOLDER = 'submissions'
QUESTION_IMG_FOLDER = 'question_images'
QUESTION_UPLOAD_DIR = os.path.join('static', 'uploads')

ALLOWED_IMAGE_EXT = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
