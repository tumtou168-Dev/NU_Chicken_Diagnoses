import os 

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
    
    # Set DATABASE_URL to override (e.g., use SQLite in dev); default is PostgreSQL.
    SQLALCHEMY_DATABASE_URI = (os.environ.get("DATABASE_URL") 
        or "postgresql://postgres:123456789@localhost:5432/chicken_diagnoses")
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Reject oversized request bodies early (profile pictures are capped at 2 MB separately).
    MAX_CONTENT_LENGTH = 4 * 1024 * 1024
