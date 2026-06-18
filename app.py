import os
from flask import Flask, abort, request
from flask_wtf.csrf import CSRFProtect
import config
from routes.auth import auth_bp
from routes.instructor import instructor_bp
from routes.student import student_bp
from routes.admin import admin_bp
from routes.courses import courses_bp
from routes.files import files_bp

csrf = CSRFProtect()


def create_app():
    app = Flask(__name__)
    app.secret_key = config.SECRET_KEY
    app.config['UPLOAD_FOLDER'] = config.UPLOAD_FOLDER
    app.config['QUESTION_IMG_FOLDER'] = config.QUESTION_IMG_FOLDER
    app.config['WTF_CSRF_ENABLED'] = True
    app.config['SESSION_COOKIE_SECURE'] = config.SESSION_COOKIE_SECURE
    app.config['SESSION_COOKIE_HTTPONLY'] = config.SESSION_COOKIE_HTTPONLY
    app.config['SESSION_COOKIE_SAMESITE'] = config.SESSION_COOKIE_SAMESITE

    os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(config.QUESTION_IMG_FOLDER, exist_ok=True)
    os.makedirs(config.QUESTION_UPLOAD_DIR, exist_ok=True)

    csrf.init_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(instructor_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(courses_bp)
    app.register_blueprint(files_bp)

    @app.before_request
    def block_public_uploads():
        if request.path.startswith('/static/uploads/'):
            abort(403)

    @app.context_processor
    def inject_config():
        return dict(config=config)

    return app


app = create_app()

if __name__ == '__main__':
    if not os.path.exists(config.DATABASE):
        print('Make sure to initialize the database via scripts/init_db.py')
    if not config.DEBUG and not config.secret_key_is_secure():
        print('ERROR: Set SECRET_KEY in .env before running without debug mode.')
        raise SystemExit(1)
    print(f'Development server: http://{config.HOST}:{config.PORT} (debug={config.DEBUG})')
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)
