import json
import os
import random
import sys
from datetime import datetime, timedelta, timezone

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
                SELECT account_number, balance
                FROM users
                WHERE is_admin = 0
                ORDER BY created_at DESC
                LIMIT :lim
                """
            ),
            {"lim": limit},
        ).fetchall()
    return [{"account_number": str(r[0]), "balance": float(r[1] or 0)} for r in rows]


def credit_phase1_from_features(*, income: float, outgoing: float, outgoing_cnt: int, balance_now: float) -> float:
    score = 0.0
    ratio = (outgoing / income) if income > 0 else (1.5 if outgoing > 0 else 0.0)

    if income <= 0 and outgoing > 0:
        score += 45
    elif ratio >= 1.2:
        score += 45
    elif ratio >= 0.9:
        score += 30
    elif ratio >= 0.7:
        score += 15

    if balance_now < 2_000:
        score += 20
    elif balance_now < 10_000:
        score += 10

    if outgoing_cnt >= 20:
        score += 15
    elif outgoing_cnt >= 12:
        score += 8

    return float(max(0.0, min(100.0, score)))


def level_from_score(score: float) -> str:
    if score >= 70:
        return "high"
    if score >= 40:
        return "medium"
    return "low"


def main(count: int = 50):
    if not table_exists("credit_risk_snapshots"):
        raise SystemExit("Table `credit_risk_snapshots` does not exist yet. Start backend once to create tables.")

    cols = get_columns("credit_risk_snapshots")
    required = {"account_number", "period_start", "period_end", "score", "level", "reasons_json", "features_json"}
    missing = required - cols
    if missing:
        raise SystemExit(f"`credit_risk_snapshots` missing required columns: {sorted(missing)}")

    if "phase1_score" not in cols or "actual_label" not in cols:
        raise SystemExit(
            "Phase-2 columns missing on `credit_risk_snapshots` (need `phase1_score` and `actual_label`). "
            "Restart backend once to apply migrations."
        )

    users = get_some_users(limit=max(200, count))
    if not users:
        raise SystemExit("No non-admin users found. Seed users first.")

    now = datetime.now(timezone.utc)
    period_end = now
    period_start = now - timedelta(days=30)

    rows = []
    for i in range(count):
        u = random.choice(users)
        acc = u["account_number"]
        balance_now = float(u["balance"] or 0.0)

        # Generate plausible 30-day aggregates.
        income = float(random.choice([0.0, 15000.0, 25000.0, 40000.0, 60000.0, 90000.0, 120000.0]))
        outgoing = float(income * random.uniform(0.4, 1.6)) if income > 0 else float(random.choice([0.0, 8000.0, 20000.0, 45000.0]))
        outgoing_cnt = int(random.choice([3, 6, 9, 12, 15, 20, 26]))

        ratio = (outgoing / income) if income > 0 else (1.5 if outgoing > 0 else 0.0)
        phase1_score = credit_phase1_from_features(
            income=income,
            outgoing=outgoing,
            outgoing_cnt=outgoing_cnt,
            balance_now=balance_now,
        )
        final_score = float(max(0.0, min(100.0, phase1_score + random.uniform(-8, 8))))
        level = level_from_score(final_score)

        # Create training label with noise: higher score -> more likely defaulted.
        p_default = 0.08 + (final_score / 100.0) * 0.75
        if ratio >= 1.2:
            p_default += 0.08
        if balance_now < 2_000:
            p_default += 0.08
        p_default = max(0.05, min(0.95, p_default))
        actual_label = "defaulted" if random.random() < p_default else "on_time"

        features = {
            "income30d": float(round(income, 2)),
            "outgoing30d": float(round(outgoing, 2)),
            "outgoingCount30d": int(outgoing_cnt),
            "outflowToInflowRatio30d": float(round(ratio, 4)),
            "balanceNow": float(round(balance_now, 2)),
        }

        reasons = [
            f"seeded snapshot {i+1}",
            f"income30d={features['income30d']}",
            f"outgoing30d={features['outgoing30d']}",
            f"ratio={features['outflowToInflowRatio30d']}",
            f"adminLabel={actual_label}",
        ]

        row = {
            "account_number": acc,
            "period_start": period_start,
            "period_end": period_end,
            "phase1_score": float(round(phase1_score, 2)),
            "score": float(round(final_score, 2)),
            "level": level,
            "actual_label": actual_label,
            "reasons_json": json.dumps(reasons),
            "features_json": json.dumps(features),
        }
        rows.append(row)

    insert_cols = sorted([c for c in rows[0].keys() if c in cols])
    stmt = f"INSERT INTO credit_risk_snapshots ({', '.join(insert_cols)}) VALUES ({', '.join(':'+c for c in insert_cols)})"

    with engine.begin() as conn:
        conn.execute(text(stmt), [{c: r[c] for c in insert_cols} for r in rows])

    print(f"Inserted {len(rows)} credit_risk_snapshots rows for Phase-2 training.")


if __name__ == "__main__":
    arg = None
    if len(sys.argv) > 1:
        try:
            arg = int(sys.argv[1])
        except Exception:
            arg = None
    main(count=arg or 50)

