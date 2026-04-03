import os
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv

# Always load `.env` next to this file (`backend/.env`), not only from the process cwd.
# Scripts run from the repo root would otherwise miss `DB_PASSWORD` and connect with no password.
_env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(_env_path)

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "jay_dee_bank")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

# Encode user/password so special characters (e.g. @, :, /) do not break the URL.
DATABASE_URL = (
    f"mysql+pymysql://{quote_plus(DB_USER)}:{quote_plus(DB_PASSWORD)}@"
    f"{DB_HOST}:{DB_PORT}/{DB_NAME}"
)
