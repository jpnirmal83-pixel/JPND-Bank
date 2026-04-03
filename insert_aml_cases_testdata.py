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


def get_some_users(limit: int = 1000) -> list[str]:
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


def _priority_from_score(score: float) -> str:
    s = float(score or 0.0)
    if s >= 90:
        return "critical"
    if s >= 75:
        return "high"
    if s >= 55:
        return "medium"
    return "low"


def _status_for_priority(priority: str) -> str:
    if priority == "critical":
        return random.choice(["escalated", "investigating", "open"])
    if priority == "high":
        return random.choice(["investigating", "open", "escalated"])
    if priority == "medium":
        return random.choice(["open", "investigating", "closed"])
    return random.choice(["open", "closed"])


def main(count: int = 50):
    table_name = "aml_cases"
    if not table_exists(table_name):
        raise SystemExit("Table `aml_cases` does not exist yet. Start backend once to create tables.")

    cols = get_columns(table_name)
    required = {
        "ring_id",
        "status",
        "priority",
        "watchlist",
        "assignee",
        "risk_score",
        "account_count",
        "accounts_json",
        "reasons_json",
        "notes",
    }
    missing = required - cols
    if missing:
        raise SystemExit(f"`{table_name}` missing required columns: {sorted(missing)}")

    users = get_some_users(limit=max(200, count * 4))
    if not users:
        raise SystemExit("No non-admin users found. Seed users first.")

    rows = []
    now = datetime.now(timezone.utc)
    teams = ["AML Team", "Fraud Ops", "Risk Desk", "Compliance"]
    for i in range(count):
        ring_id = f"RING-SEED-{i+1:03d}"
        ring_size = random.randint(2, 6)
        accounts = random.sample(users, k=min(ring_size, len(users)))
        risk_score = float(round(random.uniform(52.0, 98.0), 2))
        priority = _priority_from_score(risk_score)
        status = _status_for_priority(priority)
        watchlist = bool(risk_score >= 80.0 or random.choice([False, False, True]))
        reasons = [
            "Seeded AML case for Phase-2 operations testing.",
            "Linked accounts share suspicious network signals.",
            random.choice(
                [
                    "Shared beneficiaries across multiple accounts.",
                    "Shared device signatures found.",
                    "Common IP routing pattern observed.",
                    "Rapid fan-in/fan-out behavior.",
                ]
            ),
        ]
        rows.append(
            {
                "ring_id": ring_id,
                "status": status,
                "priority": priority,
                "watchlist": watchlist,
                "assignee": random.choice(teams),
                "risk_score": risk_score,
                "account_count": len(accounts),
                "accounts_json": json.dumps(accounts),
                "reasons_json": json.dumps(reasons),
                "notes": f"seeded row {i+1} for AML case workflow testing",
                "created_at": now,
                "updated_at": now,
            }
        )

    insert_cols = sorted([c for c in rows[0].keys() if c in cols])
    stmt = (
        f"INSERT INTO {table_name} ({', '.join(insert_cols)}) "
        f"VALUES ({', '.join(':'+c for c in insert_cols)})"
    )
    with engine.begin() as conn:
        conn.execute(text(stmt), [{c: r[c] for c in insert_cols} for r in rows])

    open_count = sum(1 for r in rows if r["status"] == "open")
    inv_count = sum(1 for r in rows if r["status"] == "investigating")
    esc_count = sum(1 for r in rows if r["status"] == "escalated")
    close_count = sum(1 for r in rows if r["status"] == "closed")
    print(
        f"Inserted {len(rows)} rows into aml_cases "
        f"(open={open_count}, investigating={inv_count}, escalated={esc_count}, closed={close_count})."
    )


if __name__ == "__main__":
    arg = None
    if len(sys.argv) > 1:
        try:
            arg = int(sys.argv[1])
        except Exception:
            arg = None
    main(count=arg or 50)
