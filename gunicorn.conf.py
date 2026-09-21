# Gunicorn settings used by the Docker image.
import os

bind = "0.0.0.0:8000"
workers = int(os.environ.get("WEB_CONCURRENCY", "2"))
timeout = 60
accesslog = "-"
errorlog = "-"

# create_app() creates tables and seeds the database when it is imported. Preloading
# runs that once in the master process instead of once per worker (which would race).
preload_app = True


def post_fork(server, worker):
    # Connections opened during preload must not be shared with forked workers.
    from extensions import db
    from run import app

    with app.app_context():
        db.engine.dispose(close=False)
