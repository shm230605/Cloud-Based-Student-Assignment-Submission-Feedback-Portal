import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def setting(name: str, default: str) -> str:
    return os.getenv(name, default)


APP_ENV = setting("APP_ENV", "development")
DATABASE_URL = setting("DATABASE_URL", "sqlite:///./portal.db")
JWT_SECRET = setting("JWT_SECRET", "local-development-only-change-before-deploy")
JWT_EXPIRE_MINUTES = int(setting("JWT_EXPIRE_MINUTES", "90"))
FRONTEND_ORIGIN = setting("FRONTEND_ORIGIN", "http://localhost:5173")
FRONTEND_ORIGINS = [origin.strip() for origin in FRONTEND_ORIGIN.split(",") if origin.strip()]
MAX_UPLOAD_MB = int(setting("MAX_UPLOAD_MB", "20"))
ALLOW_LATE_SUBMISSIONS = setting("ALLOW_LATE_SUBMISSIONS", "true").lower() == "true"
STORAGE_BACKEND = setting("STORAGE_BACKEND", "local").lower()
LOCAL_STORAGE_DIR = Path(setting("LOCAL_STORAGE_DIR", "./private_uploads"))
S3_BUCKET = setting("S3_BUCKET", "")
AWS_ENDPOINT_URL = setting("AWS_ENDPOINT_URL", "")