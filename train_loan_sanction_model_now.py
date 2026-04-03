import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
sys.path.insert(0, BACKEND_DIR)

from database import SessionLocal  # noqa: E402


def main():
    # Import after sys.path adjustment so backend imports resolve.
    import main as backend_main  # noqa: E402

    db = SessionLocal()
    try:
        res = backend_main.train_loan_sanction_model(None, db)
        print("Training result:")
        print(res.model_dump() if hasattr(res, "model_dump") else res)
    finally:
        db.close()


if __name__ == "__main__":
    main()

