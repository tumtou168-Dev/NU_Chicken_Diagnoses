FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install dependencies first so this layer is cached until requirements.txt changes.
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Run as an unprivileged user. Uploads live in the database (tbl_files); static/uploads only
# holds files from older versions, which the /media route still serves.
RUN useradd --system --uid 1000 --create-home appuser \
    && mkdir -p app/static/uploads/avatars \
    && chown -R appuser:appuser app/static/uploads
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request as u; import os; u.urlopen('http://127.0.0.1:%s/auth/login' % os.environ.get('PORT', '8000'), timeout=4)"

CMD ["gunicorn", "--config", "gunicorn.conf.py", "run:app"]
