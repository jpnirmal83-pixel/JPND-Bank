"""
Remove corrupted or incomplete DeepFace weight files so they download again on next use.

Run from the project folder:
  python fix_deepface_weights.py

Then restart the API and run KYC again.
"""
from __future__ import annotations

from pathlib import Path


def main() -> None:
    weights_dir = Path.home() / ".deepface" / "weights"
    if not weights_dir.is_dir():
        print(f"No folder at {weights_dir} (nothing to clean).")
        return

    # Common files that break verification when download was interrupted
    names = (
        "facenet_weights.h5",
        "facenet512_weights.h5",
        "vgg_face_weights.h5",
        "openface_weights.h5",
    )
    removed = 0
    for name in names:
        p = weights_dir / name
        if p.is_file():
            print(f"Removing: {p}")
            p.unlink()
            removed += 1

    if removed == 0:
        print(f"No matching weight files in {weights_dir}.")
    else:
        print(f"Removed {removed} file(s). Restart the server; DeepFace will re-download on next KYC.")


if __name__ == "__main__":
    main()
