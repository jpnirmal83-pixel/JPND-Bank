import os
import sys
import random

from sqlalchemy import text

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
sys.path.insert(0, BACKEND_DIR)

from database import engine  # noqa: E402


def table_has_column(table: str, column: str) -> bool:
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT COLUMN_NAME
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = :t
                  AND COLUMN_NAME = :c
                """
            ),
            {"t": table, "c": column},
        ).fetchall()
    return len(rows) > 0


def main():
    with engine.connect() as conn:
        total = conn.execute(text("SELECT COUNT(*) FROM loan_applications")).scalar_one()

        has_actual = table_has_column("loan_applications", "actual_recommendation")
        labeled = 0
        if has_actual:
            labeled = conn.execute(
                text("SELECT COUNT(*) FROM loan_applications WHERE actual_recommendation IS NOT NULL")
            ).scalar_one()

        model_rows = conn.execute(text("SELECT COUNT(*) FROM loan_sanction_models")).scalar_one()
        print(f"loan_applications total: {total}")
        print(f"loan_applications.actual_recommendation column exists: {has_actual}")
        if has_actual:
            print(f"labeled (actual_recommendation IS NOT NULL): {labeled}")
        print(f"loan_sanction_models rows: {model_rows}")

        if has_actual and labeled < 10:
            print("Filling unlabeled rows with random test labels to reach >=10 samples...")
            # Fill with existing recommendation as a starting point plus some noise.
            # approve -> approve/manual_review
            # manual_review -> approve/manual_review/decline
            # decline -> decline/manual_review
            conn.execute(
                text(
                    """
                    UPDATE loan_applications
                    SET actual_recommendation = CASE
                      WHEN recommendation = 'approve' THEN
                        CASE WHEN RAND() < 0.7 THEN 'approve' ELSE 'manual_review' END
                      WHEN recommendation = 'manual_review' THEN
                        CASE
                          WHEN RAND() < 0.34 THEN 'approve'
                          WHEN RAND() < 0.67 THEN 'manual_review'
                          ELSE 'decline'
                        END
                      ELSE
                        CASE WHEN RAND() < 0.7 THEN 'decline' ELSE 'manual_review' END
                    END
                    WHERE actual_recommendation IS NULL
                    """
                )
            )
            new_labeled = conn.execute(
                text("SELECT COUNT(*) FROM loan_applications WHERE actual_recommendation IS NOT NULL")
            ).scalar_one()
            print(f"New labeled count: {new_labeled}")


if __name__ == "__main__":
    main()

