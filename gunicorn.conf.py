# Gunicorn settings used by the Docker image.
import os

# Hosting platforms such as Render pass the port to listen on in $PORT.
bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"
workers = int(os.environ.get("WEB_CONCURRENCY", "4"))
# Each worker handles this many requests concurrently (I/O-bound Flask views spend most of
# their time waiting on the database, so threads let a worker serve another request meanwhile).
threads = int(os.environ.get("WEB_THREADS", "4"))
worker_class = "gthread"
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
