import json
import os
import random
import sys
import string

from sqlalchemy import text

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
sys.path.insert(0, BACKEND_DIR)

from database import engine  # noqa: E402


def get_columns(table_name: str) -> set[str]:
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT COLUMN_NAME
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = :tbl
                """
            ),
            {"tbl": table_name},
        ).fetchall()
    return {r[0] for r in rows}


def table_exists(table_name: str) -> bool:
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT COUNT(*)
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = :tbl
                """
            ),
            {"tbl": table_name},
        ).fetchall()
    return int(rows[0][0] or 0) > 0


def get_some_users(limit: int = 200):
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT account_number, balance
                FROM users
                WHERE is_admin = 0
                ORDER BY created_at DESC
                LIMIT :lim
                """
            ),
            {"lim": limit},
        ).fetchall()
    return [{"account_number": r[0], "balance": float(r[1] or 0)} for r in rows]


def compute_phase1_score(
    *,
    tx_type: str,
    amount: float,
    balance_before: float,
    hour_utc: int,
    recent_outgoing_60m: int,
    new_beneficiary: bool,
) -> tuple[float, str, list[str]]:
    score = 0.0
    reasons: list[str] = []

    if amount >= 500_000:
        score += 40
        reasons.append("High amount (>= ₹5,00,000)")
    elif amount >= 200_000:
        score += 25
        reasons.append("Large amount (>= ₹2,00,000)")

    if balance_before > 0 and (amount / balance_before) >= 0.60:
        score += 20
        reasons.append("Amount >= 60% of available balance")

    if hour_utc < 6 or hour_utc >= 22:
        score += 15
        reasons.append("Unusual transaction hour")

    if recent_outgoing_60m >= 3:
        score += 20
        reasons.append("Multiple outgoing txns last 60m")

    if tx_type == "transfer-out" and new_beneficiary:
        score += 20
        reasons.append("First transfer to new beneficiary")

    score = float(max(0.0, min(100.0, score)))
    if score >= 70:
        level = "high"
    elif score >= 40:
        level = "medium"
    else:
        level = "low"
    return score, level, reasons


def generate_insert_rows(count: int) -> list[dict]:
    users = get_some_users(limit=min(2000, max(200, count)))
    if not users:
        raise SystemExit("No non-admin users found. Seed users first.")

    rows: list[dict] = []
    for i in range(count):
        u = random.choice(users)
        acc = str(u["account_number"])
        balance_before = float(u["balance"] or 0)

        tx_type = random.choice(["withdraw", "transfer-out"])

        amount = float(
            random.choice(
                [80000.0, 120000.0, 180000.0, 260000.0, 420000.0, 550000.0, 750000.0]
            )
        )
        if balance_before > 0 and amount > balance_before:
            # Keep within a plausible user affordability band.
            amount = float(max(5000.0, min(amount, balance_before * random.uniform(0.15, 0.95))))

        hour_utc = random.randint(0, 23)
        recent_outgoing_60m = random.randint(0, 6)
        new_beneficiary = bool(tx_type == "transfer-out" and random.choice([True, False, False]))

        phase1_score, risk_level, phase1_reasons = compute_phase1_score(
            tx_type=tx_type,
            amount=amount,
            balance_before=balance_before,
            hour_utc=hour_utc,
            recent_outgoing_60m=recent_outgoing_60m,
            new_beneficiary=new_beneficiary,
        )

        # Create an admin-like ground-truth label with some noise.
        fraud_prob = 0.15 + (phase1_score / 100.0) * 0.7
        if tx_type == "transfer-out" and new_beneficiary:
            fraud_prob += 0.08
        if recent_outgoing_60m >= 4:
            fraud_prob += 0.1
        fraud_prob = max(0.05, min(0.95, fraud_prob))

        actual_label = "fraud" if random.random() < fraud_prob else "legit"

        # Training uses phase1_score + features from context_json, so keep these aligned.
        amount_to_balance_ratio = (amount / balance_before) if balance_before > 0 else 0.0
        daily_outgoing_before_total = float(balance_before * random.uniform(0.0, 0.9)) if balance_before > 0 else 0.0
        daily_outgoing_before_ratio = (daily_outgoing_before_total / balance_before) if balance_before > 0 else 0.0

        context = {
            "recentOutgoing60m": recent_outgoing_60m,
            "hourUtc": int(hour_utc),
            "newBeneficiary": bool(new_beneficiary),
            "amountToBalanceRatio": float(amount_to_balance_ratio),
            "dailyOutgoingBeforeRatio": float(daily_outgoing_before_ratio),
            "dailyWithdrawTotalBefore": float(daily_outgoing_before_total) if tx_type == "withdraw" else 0.0,
        }

        # Populate risk_score close to phase1 initially; Phase-2 will learn deviations.
        risk_score = float(round(phase1_score + random.uniform(-10, 10), 2))
        risk_score = float(max(0.0, min(100.0, risk_score)))

        reasons = [
            f"seeded test row {i+1}",
            *phase1_reasons[:3],
            f"adminLabel={actual_label}",
        ]

        row = {
            "account_number": acc,
            "transaction_type": tx_type,
            "amount": float(amount),
            "phase1_score": float(round(phase1_score, 2)),
            "risk_score": float(risk_score),
            "risk_level": risk_level if risk_level in {"low", "medium", "high"} else "low",
            "status": "reviewed",  # treated as already reviewed/labeled
            "reasons_json": json.dumps(reasons),
            "context_json": json.dumps(context),
            "actual_label": actual_label,
        }
        rows.append(row)

    return rows


def main(count: int = 50):
    if not table_exists("fraud_alerts"):
        raise SystemExit("Table `fraud_alerts` does not exist yet. Start backend once to create tables.")

    cols = get_columns("fraud_alerts")
    if not cols:
        raise SystemExit("Could not read columns for `fraud_alerts`.")

    needed = {"account_number", "transaction_type", "amount", "risk_score", "risk_level", "status", "reasons_json", "context_json"}
    missing = needed - cols
    if missing:
        raise SystemExit(f"`fraud_alerts` missing required columns: {sorted(missing)}")

    # Generate full rows and insert only columns that exist.
    rows = generate_insert_rows(count)
    insert_cols = sorted({k for r in rows for k in r.keys() if k in cols})
    if "actual_label" not in cols:
        raise SystemExit("`fraud_alerts.actual_label` column missing. Please run backend once to apply Phase-2 migrations.")

    col_list = ", ".join(insert_cols)
    placeholders = ", ".join([f":{c}" for c in insert_cols])
    stmt = f"INSERT INTO fraud_alerts ({col_list}) VALUES ({placeholders})"

    rows_filtered = [{c: r.get(c) for c in insert_cols} for r in rows]
    with engine.begin() as conn:
        conn.execute(text(stmt), rows_filtered)

    print(f"Inserted {len(rows_filtered)} fraud_alerts rows for Phase-2 training.")


if __name__ == "__main__":
    arg = None
    if len(sys.argv) > 1:
        try:
            arg = int(sys.argv[1])
        except Exception:
            arg = None
    main(count=arg or 50)

