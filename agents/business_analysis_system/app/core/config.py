from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent.parent

DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
CONTRACT_UPLOAD_DIR = UPLOAD_DIR / "contracts"
BILLING_UPLOAD_DIR = UPLOAD_DIR / "billings"
SQLITE_DIR = DATA_DIR / "sqlite"
DB_PATH = SQLITE_DIR / "ba_system.db"

for path in [DATA_DIR, UPLOAD_DIR, CONTRACT_UPLOAD_DIR, BILLING_UPLOAD_DIR, SQLITE_DIR]:
    path.mkdir(parents=True, exist_ok=True)

DATABASE_URL = f"sqlite:///{DB_PATH}"

APP_NAME = "Business Analysis System"
APP_VERSION = "0.1.0"
APP_DESCRIPTION = "MVP for business analysis intelligent agent"