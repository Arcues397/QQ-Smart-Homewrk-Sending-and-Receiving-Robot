import csv
import zipfile
from pathlib import Path
from datetime import datetime
import re

from app.config import ARCHIVE_DIR, EXPORT_DIR, DATA_DIR


SUBMISSIONS_FILE = DATA_DIR / "submissions.csv"


def sanitize_name(text: str) -> str:
    return re.sub(r'[\\/:*?"<>|]', "_", text.strip())


def build_export_name(category: str, task_id: str) -> str:
    category = sanitize_name(category)
    task_id = sanitize_name(task_id)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{category}_{task_id}_{ts}.zip"


def export_assignment_zip(category: str, task_id: str) -> Path:
    """
    打包：
    storage/archive/<类别>/<批次>/
    """
    category_safe = sanitize_name(category)
    task_id_safe = sanitize_name(task_id)

    assignment_dir = ARCHIVE_DIR / category_safe / task_id_safe
    if not assignment_dir.exists():
        raise FileNotFoundError(f"未找到作业目录：{assignment_dir}")

    export_name = build_export_name(category_safe, task_id_safe)
    export_path = EXPORT_DIR / export_name

    filtered_csv_path = EXPORT_DIR / f"_{category_safe}_{task_id_safe}_submissions_tmp.csv"
    try:
        write_filtered_submissions_csv(
            category=category,
            task_id=task_id,
            output_csv=filtered_csv_path
        )

        with zipfile.ZipFile(export_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for file_path in assignment_dir.rglob("*"):
                if file_path.is_file():
                    arcname = Path(category_safe) / task_id_safe / file_path.relative_to(assignment_dir)
                    zf.write(file_path, arcname=str(arcname))

            if filtered_csv_path.exists():
                zf.write(
                    filtered_csv_path,
                    arcname=str(Path(category_safe) / task_id_safe / "reports" / "submissions.csv")
                )

    finally:
        if filtered_csv_path.exists():
            filtered_csv_path.unlink(missing_ok=True)

    return export_path


def write_filtered_submissions_csv(category: str, task_id: str, output_csv: Path):
    if not SUBMISSIONS_FILE.exists():
        return

    with open(SUBMISSIONS_FILE, "r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = [
            row for row in reader
            if row.get("category") == category and row.get("task_id") == task_id
        ]

    if not rows:
        return

    with open(output_csv, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=reader.fieldnames)
        writer.writeheader()
        writer.writerows(rows)