import json
import random

import os
import sys
from datetime import date

from sqlalchemy import text

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
sys.path.insert(0, BACKEND_DIR)

from database import engine


def get_columns():
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT COLUMN_NAME
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'loan_applications'
                """
            )
        ).fetchall()
    return {r[0] for r in rows}


def get_some_users(limit=10):
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
    return [r[0] for r in rows]


def estimate_emi(principal: float, annual_rate: float, n_months: int) -> float:
    P = float(principal or 0)
    if P <= 0 or n_months <= 0:
        return 0.0
    r = float(annual_rate or 0) / 12.0 / 100.0
    if r == 0:
        return P / float(n_months)
    pow_term = (1 + r) ** n_months
    return (P * r * pow_term) / (pow_term - 1)


def apr_for_loan_type(loan_type: str) -> float:
    lt = (loan_type or "").lower()
    mapping = {
        "personal": 14.0,
        "home": 8.5,
        "vehicle": 10.0,
        "business": 12.0,
    }
    return mapping.get(lt, 12.0)


def main(count: int = 10):
    cols = get_columns()
    required = {"loan_type", "loan_amount", "tenure_months", "monthly_income", "existing_emi_total", "secured", "estimated_emi", "dti", "sanction_score", "recommendation", "reasons_json", "account_number"}
    missing = required - cols
    if missing:
        raise SystemExit(f"loan_applications table missing required columns: {sorted(missing)}")

    users = get_some_users(count)
    if not users:
        raise SystemExit("No non-admin users found in `users` table. Seed users first.")

    # Ensure we can insert N rows even if fewer users exist.
    while len(users) < count:
        users.append(random.choice(users))

    loan_types = ["personal", "home", "vehicle", "business"]

    inserts = []
    for i in range(count):
        account_number = users[i]
        loan_type = random.choice(loan_types)
        loan_amount = random.choice([500000.0, 700000.0, 1000000.0, 1500000.0, 2500000.0])
        tenure_months = random.choice([24, 36, 48, 60, 72, 84])
        monthly_income = random.choice([40000.0, 60000.0, 80000.0, 100000.0, 150000.0])
        existing_emi_total = random.choice([0.0, 5000.0, 10000.0, 20000.0])
        credit_score = random.choice([None, 620, 680, 720, 760])

        secured = random.choice([True, False])
        collateral_value = None
        ltv = None
        if secured:
            # Keep LTV in a reasonable band (70% to 100%)
            collateral_value = max(1.0, loan_amount / random.uniform(0.7, 1.0))
            ltv = loan_amount / collateral_value

        apr = apr_for_loan_type(loan_type)
        estimated_emi = float(estimate_emi(loan_amount, apr, tenure_months))
        dti = float((existing_emi_total + estimated_emi) / monthly_income)

        # Use the same Phase-1 thresholds to create a plausible initial recommendation.
        if dti <= 0.45:
            recommendation = "approve"
        elif dti <= 0.6:
            recommendation = "manual_review"
        else:
            recommendation = "decline"

        # sanction_score: 0..100 scaled from dti bucket.
        sanction_score = float(max(0.0, min(100.0, (0.7 - dti) * 220.0))) if dti is not None else 0.0
        sanction_score = round(sanction_score, 2)

        reasons = [
            f"seeded test row {i+1}",
            f"loan_type={loan_type}",
            f"estimated_emi={estimated_emi:.2f}",
            f"dti={dti:.4f}",
        ]

        row = {
            "account_number": account_number,
            "loan_type": loan_type,
            "loan_amount": float(loan_amount),
            "tenure_months": int(tenure_months),
            "monthly_income": float(monthly_income),
            "existing_emi_total": float(existing_emi_total),
            "credit_score": credit_score,
            "secured": bool(secured),
            "collateral_value": float(collateral_value) if collateral_value is not None else None,
            "estimated_emi": float(estimated_emi),
            "dti": float(dti),
            "sanction_score": float(sanction_score),
            "recommendation": recommendation,
            "reasons_json": json.dumps(reasons),
        }

        if "dob" in cols:
            # 18..60 years old, stored as YYYY-MM-DD (compatible with backend parser).
            age_years = random.randint(18, 60)
            month = random.randint(1, 12)
            day = random.randint(1, 28)
            dob_dt = date.today().replace(year=date.today().year - age_years, month=month, day=day)
            row["dob"] = dob_dt.isoformat()

        if "actual_recommendation" in cols:
            # Create a slightly noisy label so training has signal.
            if recommendation == "approve":
                row["actual_recommendation"] = random.choice(["approve", "manual_review"])
            elif recommendation == "manual_review":
                row["actual_recommendation"] = random.choice(["manual_review", "decline", "approve"])
            else:
                row["actual_recommendation"] = random.choice(["decline", "manual_review"])

        inserts.append(row)

    insert_cols = sorted({k for r in inserts for k in r.keys() if k in cols})
    if "actual_recommendation" in insert_cols:
        pass

    placeholders = ", ".join([f":{c}" for c in insert_cols])
    col_list = ", ".join(insert_cols)
    stmt = f"INSERT INTO loan_applications ({col_list}) VALUES ({placeholders})"

    with engine.begin() as conn:
        conn.execute(text(stmt), inserts[0] if len(inserts) == 1 else inserts)

    print(f"Inserted {count} loan_applications test rows.")


if __name__ == "__main__":
    arg = None
    if len(sys.argv) > 1:
        try:
            arg = int(sys.argv[1])
        except Exception:
            arg = None
    main(count=arg or 10)

