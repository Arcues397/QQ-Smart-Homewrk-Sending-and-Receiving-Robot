import csv
from datetime import datetime
from pathlib import Path

from app.config import DATA_DIR


SUBMISSIONS_FILE = DATA_DIR / "submissions.csv"

FIELDNAMES = [
    "submit_time",
    "openid",
    "category",
    "task_id",
    "student_id",
    "name",
    "original_filename",
    "saved_filename",
    "saved_path",
    "replaced_old",
    "duplicate_path",
]


def ensure_submissions_file():
    if not SUBMISSIONS_FILE.exists():
        with open(SUBMISSIONS_FILE, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()


def append_submission_record(
    openid: str,
    category: str,
    task_id: str,
    student_id: str,
    name: str,
    original_filename: str,
    saved_path: Path,
    replaced_old: bool,
    duplicate_path: Path | None,
):
    ensure_submissions_file()

    row = {
        "submit_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "openid": openid,
        "category": category,
        "task_id": task_id,
        "student_id": student_id,
        "name": name,
        "original_filename": original_filename,
        "saved_filename": saved_path.name,
        "saved_path": str(saved_path),
        "replaced_old": "yes" if replaced_old else "no",
        "duplicate_path": str(duplicate_path) if duplicate_path else "",
    }

    with open(SUBMISSIONS_FILE, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writerow(row)