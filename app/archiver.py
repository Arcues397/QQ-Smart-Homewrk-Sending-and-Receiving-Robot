from pathlib import Path
import shutil
import re
from datetime import datetime

from app.config import ARCHIVE_DIR


def sanitize_name(text: str) -> str:
    return re.sub(r'[\\/:*?"<>|]', "_", text.strip())


def render_filename(template: str, student_id: str, name: str, category: str, task_id: str) -> str:
    filename = template.format(
        student_id=student_id,
        name=name,
        category=category,
        task_id=task_id,
    )

    filename = sanitize_name(filename)

    if not filename.lower().endswith(".pdf"):
        filename += ".pdf"

    return filename


def archive_submission(
    downloaded_file: Path,
    category: str,
    task_id: str,
    student_id: str,
    name: str,
    filename_template: str
) -> dict:
    category_safe = sanitize_name(category)
    task_id_safe = sanitize_name(task_id)

    valid_dir = ARCHIVE_DIR / category_safe / task_id_safe / "valid"
    duplicate_dir = ARCHIVE_DIR / category_safe / task_id_safe / "duplicate"

    valid_dir.mkdir(parents=True, exist_ok=True)
    duplicate_dir.mkdir(parents=True, exist_ok=True)

    new_filename = render_filename(
        template=filename_template,
        student_id=student_id,
        name=name,
        category=category,
        task_id=task_id,
    )

    target_path = valid_dir / new_filename
    duplicate_path = None
    replaced_old = False

    if target_path.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        stem = target_path.stem
        suffix = target_path.suffix
        duplicate_path = duplicate_dir / f"{stem}_old_{timestamp}{suffix}"
        shutil.move(str(target_path), str(duplicate_path))
        replaced_old = True

    shutil.move(str(downloaded_file), str(target_path))

    return {
        "final_path": target_path,
        "duplicate_path": duplicate_path,
        "replaced_old": replaced_old,
    }