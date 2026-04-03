import json
import os
import random
import sys
from datetime import datetime, timezone

from sqlalchemy import text

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
sys.path.insert(0, BACKEND_DIR)

from database import engine  # noqa: E402


def table_exists(table_name: str) -> bool:
    with engine.connect() as conn:
        n = conn.execute(
            text(
                """
                SELECT COUNT(*)
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = :t
                """
            ),
            {"t": table_name},
        ).scalar()
    return int(n or 0) > 0


def get_columns(table_name: str) -> set[str]:
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT COLUMN_NAME
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = :t
                """
            ),
            {"t": table_name},
        ).fetchall()
    return {r[0] for r in rows}


def get_some_users(limit: int = 500):
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT account_number
                FROM users
                WHERE is_admin = 0
                ORDER BY created_at DESC
                LIMIT :lim
                """
            ),
            {"lim": limit},
        ).fetchall()
    return [str(r[0]) for r in rows]


def _sample_doc_row(i: int, account_number: str, now: datetime):
    # Balanced labels for model training.
    doc_type = "salary_slip" if i % 2 == 0 else "bank_statement"
    confidence = round(random.uniform(0.62, 0.96), 4)

    if doc_type == "salary_slip":
        monthly_income = float(random.choice([28000, 35000, 42000, 56000, 73000, 91000]))
        emi = float(random.choice([0, 2500, 4500, 7000, 12000]))
        review_status = random.choice(["approved", "needs_correction"])
        corrected_doc_type = doc_type
        corrected_income = monthly_income * random.uniform(0.95, 1.08) if review_status == "needs_correction" else None
        corrected_emi = emi * random.uniform(0.9, 1.1) if review_status == "needs_correction" and emi > 0 else None
    else:
        monthly_income = float(random.choice([25000, 32000, 48000, 60000, 78000]))
        emi = float(random.choice([1200, 3000, 5200, 9000, 15000]))
        review_status = random.choice(["approved", "needs_correction"])
        corrected_doc_type = doc_type
        corrected_income = monthly_income * random.uniform(0.93, 1.12) if review_status == "needs_correction" else None
        corrected_emi = emi * random.uniform(0.9, 1.12) if review_status == "needs_correction" else None

    income_verification_status = random.choice(["verified", "mismatch", "not_checked"])
    file_name = f"{doc_type}_{i+1}.png"
    text_preview = (
        f"{doc_type} sample OCR content for account {account_number}. "
        f"monthly salary {monthly_income:.2f}, emi {emi:.2f}, reviewed {review_status}."
    )
    extracted_json = {
        "documentType": doc_type,
        "monthlyIncome": monthly_income,
        "existingEmiTotal": emi,
        "fileName": file_name,
    }

    return {
        "account_number": account_number,
        "file_name": file_name,
        "document_type": doc_type,
        "monthly_income_extracted": monthly_income,
        "emi_extracted": emi,
        "income_verification_status": income_verification_status,
        "confidence": confidence,
        "corrected_document_type": corrected_doc_type if review_status != "rejected" else None,
        "corrected_monthly_income": float(round(corrected_income, 2)) if corrected_income is not None else None,
        "corrected_emi": float(round(corrected_emi, 2)) if corrected_emi is not None else None,
        "review_status": review_status,
        "reviewer_notes": (
            "seeded: corrected values after admin review"
            if review_status == "needs_correction"
            else "seeded: approved extraction"
        ),
        "reviewed_at": now,
        "raw_text_preview": text_preview,
        "extracted_json": json.dumps(extracted_json),
        "created_at": now,
    }


def main(count: int = 50):
    table_name = "loan_document_ai_logs"
    if not table_exists(table_name):
        raise SystemExit("Table `loan_document_ai_logs` does not exist yet. Start backend once to create tables.")

    cols = get_columns(table_name)
    required = {
        "account_number",
        "file_name",
        "document_type",
        "monthly_income_extracted",
        "emi_extracted",
        "income_verification_status",
        "confidence",
        "raw_text_preview",
        "extracted_json",
    }
    missing = required - cols
    if missing:
        raise SystemExit(f"`{table_name}` missing required columns: {sorted(missing)}")

    phase2_cols = {
        "corrected_document_type",
        "corrected_monthly_income",
        "corrected_emi",
        "review_status",
        "reviewer_notes",
        "reviewed_at",
    }
    if not phase2_cols.issubset(cols):
        raise SystemExit(
            "Phase-2 review columns missing on `loan_document_ai_logs`. "
            "Restart backend once to apply migrations, then re-run."
        )

    users = get_some_users(limit=max(200, count))
    if not users:
        raise SystemExit("No non-admin users found. Seed users first.")

    now = datetime.now(timezone.utc)
    rows = []
    for i in range(count):
        account_number = random.choice(users)
        rows.append(_sample_doc_row(i, account_number, now))

    insert_cols = sorted([c for c in rows[0].keys() if c in cols])
    stmt = (
        f"INSERT INTO {table_name} ({', '.join(insert_cols)}) "
        f"VALUES ({', '.join(':'+c for c in insert_cols)})"
    )
    with engine.begin() as conn:
        conn.execute(text(stmt), [{c: r[c] for c in insert_cols} for r in rows])

    salary_count = sum(1 for r in rows if r["document_type"] == "salary_slip")
    bank_count = sum(1 for r in rows if r["document_type"] == "bank_statement")
    print(
        f"Inserted {len(rows)} rows into loan_document_ai_logs "
        f"(salary_slip={salary_count}, bank_statement={bank_count})."
    )


if __name__ == "__main__":
    arg = None
    if len(sys.argv) > 1:
        try:
            arg = int(sys.argv[1])
        except Exception:
            arg = None
    main(count=arg or 50)

