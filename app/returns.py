import csv
from datetime import datetime

from app.config import DATA_DIR


RETURNS_FILE = DATA_DIR / "returns.csv"

FIELDNAMES = [
    "return_time",
    "category",
    "task_id",
    "student_id",
    "original_filename",
    "saved_filename",
    "saved_path",
]


def ensure_returns_file():
    if not RETURNS_FILE.exists():
        with open(RETURNS_FILE, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()


def append_return_record(
    category: str,
    task_id: str,
    student_id: str,
    original_filename: str,
    saved_path,
):
    ensure_returns_file()

    row = {
        "return_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "category": category,
        "task_id": task_id,
        "student_id": student_id,
        "original_filename": original_filename,
        "saved_filename": saved_path.name,
        "saved_path": str(saved_path),
    }

    with open(RETURNS_FILE, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writerow(row)


def find_return_file(category: str, task_id: str, student_id: str):
    ensure_returns_file()

    with open(RETURNS_FILE, "r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        matched = [
            row for row in reader
            if row.get("category") == category
            and row.get("task_id") == task_id
            and row.get("student_id") == student_id
        ]

    if not matched:
        return None

    return matched[-1]