import os
import sys
import json

from sqlalchemy import text

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
sys.path.insert(0, BACKEND_DIR)

from database import engine  # noqa: E402


def main():
    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT trained_at, weights_json, feature_means_json, feature_stds_json, metrics_json
                FROM loan_sanction_models
                ORDER BY trained_at DESC
                LIMIT 1
                """
            )
        ).fetchone()

    if not row:
        print("No model rows found.")
        return

    trained_at = row[0]
    weights_json = row[1]
    means_json = row[2]
    stds_json = row[3]
    metrics_json = row[4]

    print("trained_at:", trained_at)
    print("metrics:", metrics_json)

    try:
        wblob = json.loads(weights_json or "{}")
        print("bias:", wblob.get("bias", 0.0))
        print("weights:", wblob.get("weights", []))
    except Exception:
        print("weights_json (raw):", weights_json)

    try:
        print("feature_means:", json.loads(means_json or "[]"))
        print("feature_stds:", json.loads(stds_json or "[]"))
    except Exception:
        print("feature_means_json (raw):", means_json)
        print("feature_stds_json (raw):", stds_json)


if __name__ == "__main__":
    main()

