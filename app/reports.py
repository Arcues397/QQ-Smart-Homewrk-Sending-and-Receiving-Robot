import csv
import re
from datetime import datetime

from app.config import DATA_DIR, EXPORT_DIR
from app.student_registry import load_students


SUBMISSIONS_FILE = DATA_DIR / "submissions.csv"


def sanitize_name(text: str) -> str:
    return re.sub(r'[\\/:*?"<>|]', "_", text.strip())


def load_latest_submissions(category: str, task_id: str) -> dict[str, dict]:
    latest = {}

    if not SUBMISSIONS_FILE.exists():
        return latest

    with open(SUBMISSIONS_FILE, "r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("category") != category or row.get("task_id") != task_id:
                continue

            student_id = (row.get("student_id") or "").strip()
            if student_id:
                latest[student_id] = row

    return latest


def generate_submitted_report(category: str, task_id: str):
    latest = load_latest_submissions(category, task_id)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"已交_{sanitize_name(category)}_{sanitize_name(task_id)}_{ts}.csv"
    output_path = EXPORT_DIR / filename

    fieldnames = [
        "student_id",
        "name",
        "submit_time",
        "saved_filename",
        "original_filename",
        "replaced_old",
    ]

    rows = []
    for student_id in sorted(latest.keys()):
        row = latest[student_id]
        rows.append({
            "student_id": student_id,
            "name": row.get("name", ""),
            "submit_time": row.get("submit_time", ""),
            "saved_filename": row.get("saved_filename", ""),
            "original_filename": row.get("original_filename", ""),
            "replaced_old": row.get("replaced_old", ""),
        })

    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return {
        "path": output_path,
        "count": len(rows),
    }


def generate_missing_report(category: str, task_id: str):
    students = load_students()
    latest = load_latest_submissions(category, task_id)
    submitted_ids = set(latest.keys())

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"缺交_{sanitize_name(category)}_{sanitize_name(task_id)}_{ts}.csv"
    output_path = EXPORT_DIR / filename

    fieldnames = ["student_id", "name"]

    rows = []
    for student_id in sorted(students.keys()):
        if student_id not in submitted_ids:
            rows.append({
                "student_id": student_id,
                "name": students[student_id],
            })

    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return {
        "path": output_path,
        "count": len(rows),
        "total": len(students),
        "submitted": len(submitted_ids),
    }