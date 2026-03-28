import csv
import re
import shutil
import zipfile
from datetime import datetime
from pathlib import Path

from app.config import DATA_DIR, STORAGE_DIR, TEMP_DIR
from app.returns import append_return_record


SUBMISSIONS_FILE = DATA_DIR / "submissions.csv"


def sanitize_name(text: str) -> str:
    return re.sub(r'[\\/:*?"<>|]', "_", text.strip())


def normalize_filename(name: str) -> str:
    return name.strip().casefold()


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path

    stem = path.stem
    suffix = path.suffix
    parent = path.parent

    i = 1
    while True:
        candidate = parent / f"{stem}_{i}{suffix}"
        if not candidate.exists():
            return candidate
        i += 1


def build_submission_indexes(category: str, task_id: str):
    saved_index = {}
    original_index = {}

    if not SUBMISSIONS_FILE.exists():
        return saved_index, original_index

    with open(SUBMISSIONS_FILE, "r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("category") != category or row.get("task_id") != task_id:
                continue

            student_id = (row.get("student_id") or "").strip()
            saved_filename = (row.get("saved_filename") or "").strip()
            original_filename = (row.get("original_filename") or "").strip()

            if student_id and saved_filename:
                saved_index[normalize_filename(saved_filename)] = student_id

            if student_id and original_filename:
                original_index[normalize_filename(original_filename)] = student_id

    return saved_index, original_index


def import_return_zip(zip_file_path: str | Path, category: str, task_id: str):
    """
    导入老师返还的 zip：
    1. 保存原 zip
    2. 解压
    3. 用文件名匹配 submissions.csv
    4. 匹配成功的登记到 returns.csv
    5. 匹配失败的放 unmatched
    """
    zip_file_path = Path(zip_file_path)

    category_safe = sanitize_name(category)
    task_id_safe = sanitize_name(task_id)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    corrected_root = STORAGE_DIR / "corrected" / category_safe / task_id_safe
    imported_zip_dir = corrected_root / "imported_zip"
    matched_dir = corrected_root / "matched"
    unmatched_dir = corrected_root / "unmatched"
    extract_dir = TEMP_DIR / f"return_import_{category_safe}_{task_id_safe}_{ts}"

    imported_zip_dir.mkdir(parents=True, exist_ok=True)
    matched_dir.mkdir(parents=True, exist_ok=True)
    unmatched_dir.mkdir(parents=True, exist_ok=True)
    extract_dir.mkdir(parents=True, exist_ok=True)

    # 保存老师返还原包
    stored_zip_name = f"{ts}__{sanitize_name(zip_file_path.name)}"
    stored_zip_path = unique_path(imported_zip_dir / stored_zip_name)
    shutil.move(str(zip_file_path), str(stored_zip_path))

    # 解压
    with zipfile.ZipFile(stored_zip_path, "r") as zf:
        zf.extractall(extract_dir)

    saved_index, original_index = build_submission_indexes(category, task_id)

    matched_count = 0
    unmatched_count = 0
    unmatched_files = []

    try:
        for file_path in extract_dir.rglob("*"):
            if not file_path.is_file():
                continue

            filename = file_path.name
            filename_key = normalize_filename(filename)

            student_id = saved_index.get(filename_key)
            if student_id is None:
                student_id = original_index.get(filename_key)

            if student_id:
                student_dir = matched_dir / student_id
                student_dir.mkdir(parents=True, exist_ok=True)

                target_path = unique_path(student_dir / sanitize_name(filename))
                shutil.move(str(file_path), str(target_path))

                append_return_record(
                    category=category,
                    task_id=task_id,
                    student_id=student_id,
                    original_filename=filename,
                    saved_path=target_path,
                )
                matched_count += 1
            else:
                target_path = unique_path(unmatched_dir / sanitize_name(filename))
                shutil.move(str(file_path), str(target_path))
                unmatched_count += 1
                unmatched_files.append(filename)

    finally:
        if extract_dir.exists():
            shutil.rmtree(extract_dir, ignore_errors=True)

    return {
        "stored_zip_path": stored_zip_path,
        "matched_count": matched_count,
        "unmatched_count": unmatched_count,
        "unmatched_files": unmatched_files,
    }