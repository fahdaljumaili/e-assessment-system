"""Production entry point (Waitress WSGI server)."""
import sys

import config
from app import app

if __name__ == '__main__':
    if not config.secret_key_is_secure():
        print('ERROR: Set a strong SECRET_KEY in .env before running in production.', file=sys.stderr)
        sys.exit(1)
    if config.DEBUG:
        print('WARNING: FLASK_DEBUG=1 — set FLASK_DEBUG=0 for production.', file=sys.stderr)

    from waitress import serve

    print(f'Starting production server on http://{config.HOST}:{config.PORT}')
    serve(app, host=config.HOST, port=config.PORT, threads=4)
