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
                SELECT account_number, balance, created_at
                FROM users
                WHERE is_admin = 0
                ORDER BY created_at DESC
                LIMIT :lim
                """
            ),
            {"lim": limit},
        ).fetchall()
    out = []
    for acc, bal, created_at in rows:
        out.append(
            {
                "account_number": str(acc),
                "balance": float(bal or 0.0),
                "created_at": created_at,
            }
        )
    return out


def churn_phase1_from_features(*, days_inactive: int | None, txn_count_30d: int, balance_now: float) -> float:
    score = 0.0
    if days_inactive is None:
        score += 35
    elif days_inactive >= 45:
        score += 55
    elif days_inactive >= 21:
        score += 35
    elif days_inactive >= 10:
        score += 15

    if txn_count_30d <= 1:
        score += 25
    elif txn_count_30d <= 3:
        score += 15

    if balance_now <= 500:
        score += 15
    elif balance_now <= 2000:
        score += 8

    return float(max(0.0, min(100.0, score)))


def level_from_score(score: float) -> str:
    if score >= 70:
        return "high"
    if score >= 40:
        return "medium"
    return "low"


def main(count: int = 50):
    if not table_exists("churn_snapshots"):
        raise SystemExit("Table `churn_snapshots` does not exist yet. Start backend once to create tables.")

    cols = get_columns("churn_snapshots")
    required = {"account_number", "score", "level", "reasons_json", "features_json"}
    missing = required - cols
    if missing:
        raise SystemExit(f"`churn_snapshots` missing required columns: {sorted(missing)}")

    if "phase1_score" not in cols or "actual_label" not in cols:
        raise SystemExit(
            "Phase-2 columns missing on `churn_snapshots` (need `phase1_score` and `actual_label`). "
            "Restart backend once to apply migrations."
        )

    users = get_some_users(limit=max(200, count))
    if not users:
        raise SystemExit("No non-admin users found. Seed users first.")

    now = datetime.now(timezone.utc)
    rows = []
    for i in range(count):
        u = random.choice(users)
        acc = u["account_number"]
        balance_now = float(u["balance"] or 0.0)

        days_inactive = random.choice([None, 2, 5, 11, 18, 25, 38, 50, 65])
        txn_count_30d = int(random.choice([0, 1, 2, 3, 5, 8, 12]))

        phase1_score = churn_phase1_from_features(
            days_inactive=days_inactive, txn_count_30d=txn_count_30d, balance_now=balance_now
        )
        final_score = float(max(0.0, min(100.0, phase1_score + random.uniform(-8, 8))))
        level = level_from_score(final_score)

        # Label with noise: higher score => more likely churned
        p_churn = 0.10 + (final_score / 100.0) * 0.75
        if (days_inactive or 0) >= 45:
            p_churn += 0.08
        if txn_count_30d <= 1:
            p_churn += 0.06
        if balance_now <= 500:
            p_churn += 0.05
        p_churn = max(0.05, min(0.95, p_churn))
        actual_label = "churned" if random.random() < p_churn else "retained"

        features = {
            "daysInactive": days_inactive,
            "txnCount30d": txn_count_30d,
            "balanceNow": float(round(balance_now, 2)),
        }
        reasons = [
            f"seeded churn snapshot {i+1}",
            f"daysInactive={days_inactive}",
            f"txnCount30d={txn_count_30d}",
            f"adminLabel={actual_label}",
        ]

        row = {
            "account_number": acc,
            "phase1_score": float(round(phase1_score, 2)),
            "score": float(round(final_score, 2)),
            "level": level,
            "actual_label": actual_label,
            "reasons_json": json.dumps(reasons),
            "features_json": json.dumps(features),
            "created_at": now,
        }
        rows.append(row)

    insert_cols = sorted([c for c in rows[0].keys() if c in cols])
    stmt = f"INSERT INTO churn_snapshots ({', '.join(insert_cols)}) VALUES ({', '.join(':'+c for c in insert_cols)})"
    with engine.begin() as conn:
        conn.execute(text(stmt), [{c: r[c] for c in insert_cols} for r in rows])

    print(f"Inserted {len(rows)} churn_snapshots rows for Phase-2 training.")


if __name__ == "__main__":
    arg = None
    if len(sys.argv) > 1:
        try:
            arg = int(sys.argv[1])
        except Exception:
            arg = None
    main(count=arg or 50)

