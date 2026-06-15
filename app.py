import os
from flask import Flask, send_from_directory
from flask_wtf.csrf import CSRFProtect
import config
from routes.auth import auth_bp
from routes.instructor import instructor_bp
from routes.student import student_bp
from routes.admin import admin_bp
from routes.courses import courses_bp

csrf = CSRFProtect()


def create_app():
    app = Flask(__name__)
    app.secret_key = config.SECRET_KEY
    app.config['UPLOAD_FOLDER'] = config.UPLOAD_FOLDER
    app.config['QUESTION_IMG_FOLDER'] = config.QUESTION_IMG_FOLDER
    app.config['WTF_CSRF_ENABLED'] = True

    os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(config.QUESTION_IMG_FOLDER, exist_ok=True)
    os.makedirs(config.QUESTION_UPLOAD_DIR, exist_ok=True)

    csrf.init_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(instructor_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(courses_bp)

    @app.context_processor
    def inject_config():
        return dict(config=config)

    @app.route('/submissions/<path:filename>', endpoint='download_submission')
    def download_submission(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    @app.route('/question_images/<path:filename>', endpoint='question_image')
    def question_image(filename):
        return send_from_directory(app.config['QUESTION_IMG_FOLDER'], filename)

    return app


app = create_app()

if __name__ == '__main__':
    if not os.path.exists(config.DATABASE):
        print('Make sure to initialize the database via scripts/init_db.py')
    debug = os.getenv('FLASK_DEBUG', '1') == '1'
    app.run(host='0.0.0.0', port=5000, debug=debug)
