import os
import sys
import json
import random
import string

from sqlalchemy import text
from passlib.context import CryptContext


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
sys.path.insert(0, BACKEND_DIR)

from database import engine  # noqa: E402


CRYPT = CryptContext(schemes=["bcrypt"], deprecated="auto")
TEST_PASSWORD = "Test@12345"


def get_columns():
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT COLUMN_NAME
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'users'
                """
            )
        ).fetchall()
    return {r[0] for r in rows}


def get_next_account_number():
    # Mimic the existing create_user behavior: next numeric account beyond current max.
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT account_number
                FROM users
                WHERE is_admin = 0
                """
            )
        ).fetchall()

    numeric = []
    for (acc,) in rows:
        if acc and str(acc).isdigit():
            numeric.append(int(acc))
    if not numeric:
        return 700010001
    return max(numeric) + 1


def main(count: int = 500):
    cols = get_columns()
    required = {"name", "email", "phone", "account_number", "password", "is_admin"}
    missing = required - cols
    if missing:
        raise SystemExit(f"users table missing required columns: {sorted(missing)}")

    start_acc = get_next_account_number()
    pwd_hash = CRYPT.hash(TEST_PASSWORD)

    # Prepare insert column list.
    insert_cols = sorted(list(cols & required))  # start with required
    # Add optional commonly used columns if they exist.
    optional_defaults = {
        "gender": "",
        "dob": "",
        "address": "",
        "balance": 0.0,
        "transactions_json": "[]",
        "created_at": None,  # use server default if present
    }
    for k, v in optional_defaults.items():
        if k in cols and k not in insert_cols and v is not None:
            insert_cols.append(k)

    # If created_at exists, omit it so server default is used.
    insert_cols = [c for c in insert_cols if c != "created_at"]

    def rand_dob():
        # DD/MM/YYYY-ish but stored as string; keep it simple.
        year = random.randint(1975, 2005)
        month = random.randint(1, 12)
        day = random.randint(1, 28)
        return f"{day:02d}/{month:02d}/{year}"

    def rand_name(i: int):
        first = random.choice(["Jithesh", "Nirmala", "Arun", "Karthik", "Sakthi", "Priya", "Ravi", "Divya"])
        last = random.choice(["K", "S", "R", "V", "M", "T", "N"])
        return f"{first} {last} {i}"

    rows = []
    used_accounts = set()

    for i in range(count):
        acc = start_acc + i
        while acc in used_accounts:
            acc += 1
        used_accounts.add(acc)

        email = f"testuser_{acc}_{i}@example.com"
        phone = "9" + "".join(random.choice(string.digits) for _ in range(9))

        row = {
            "name": rand_name(i),
            "email": email,
            "phone": phone,
            "account_number": str(acc),
            "password": pwd_hash,
            "is_admin": 0,
        }

        if "gender" in cols:
            row["gender"] = random.choice(["", "Male", "Female", "Other"])
        if "dob" in cols:
            row["dob"] = rand_dob()
        if "address" in cols:
            row["address"] = f"Test Street {i}"
        if "balance" in cols:
            row["balance"] = float(random.choice([0, 5000, 10000, 20000, 50000, 100000]))
        if "transactions_json" in cols:
            row["transactions_json"] = json.dumps([])

        # Ensure row includes only columns we are inserting.
        row_final = {c: row.get(c) for c in insert_cols}
        # Drop any keys that still aren't set (shouldn't happen).
        row_final = {k: v for k, v in row_final.items() if v is not None or k in {"gender"}}
        rows.append(row_final)

    col_list = ", ".join(insert_cols)
    placeholders = ", ".join([f":{c}" for c in insert_cols])
    stmt = f"INSERT INTO users ({col_list}) VALUES ({placeholders})"

    with engine.begin() as conn:
        conn.execute(text(stmt), rows)

    print(f"Inserted {len(rows)} users into `users` for testing.")
    print(f"Test password for all inserted users: {TEST_PASSWORD}")


if __name__ == "__main__":
    main(500)

