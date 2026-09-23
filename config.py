import os 

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
    
    # Set DATABASE_URL to override (e.g., use SQLite in dev); default is PostgreSQL.
    SQLALCHEMY_DATABASE_URI = (os.environ.get("DATABASE_URL") 
        or "postgresql://postgres:123456789@localhost:5432/chicken_diagnoses")
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Language display. False (default): show only the language chosen with the ខ្មែរ | EN switch.
    # True: show Khmer and English together everywhere, the chosen language first.
    # Change it here, or set SHOW_BOTH_LANGUAGES=1 in the environment. Restart the app after changing it.
    SHOW_BOTH_LANGUAGES = os.environ.get("SHOW_BOTH_LANGUAGES", "0") == "1"

    # Google OAuth 2.0 Credentials
    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")

    # SMTP Mail Configuration (Password Reset)
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", "587"))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "1") == "1"
    MAIL_USE_SSL = os.environ.get("MAIL_USE_SSL", "0") == "1"
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", "")

    # Reject oversized request bodies early. Phone photos are often 5-10 MB; profile and chat
    # pictures are shrunk after upload, so this only needs to fit an unedited photo.
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
