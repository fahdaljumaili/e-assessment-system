import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

_INSECURE_SECRET = 'replace_with_secure_random_string'


def _load_dotenv():
    env_path = BASE_DIR / '.env'
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, _, value = line.partition('=')
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()


def env_bool(name, default=False):
    val = os.getenv(name, '1' if default else '0').strip().lower()
    return val in ('1', 'true', 'yes', 'on')


SECRET_KEY = os.getenv('SECRET_KEY', _INSECURE_SECRET)
DEBUG = env_bool('FLASK_DEBUG', default=True)
HOST = os.getenv('HOST', '0.0.0.0')
PORT = int(os.getenv('PORT', '5000'))

DATABASE = os.getenv('DATABASE', 'db.sqlite3')
UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'submissions')
QUESTION_IMG_FOLDER = os.getenv('QUESTION_IMG_FOLDER', 'question_images')
QUESTION_UPLOAD_DIR = os.path.join('static', 'uploads')

ALLOWED_IMAGE_EXT = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# Enable SESSION_COOKIE_SECURE=1 when serving over HTTPS
SESSION_COOKIE_SECURE = env_bool('SESSION_COOKIE_SECURE', default=False)
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'


def secret_key_is_secure():
    return SECRET_KEY and SECRET_KEY != _INSECURE_SECRET
