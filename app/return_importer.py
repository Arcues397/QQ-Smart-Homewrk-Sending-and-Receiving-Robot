import csv
import hashlib
import json
import os
from tempfile import NamedTemporaryFile
import re
import shutil
import zipfile
from datetime import datetime
from pathlib import Path

from app.config import DATA_DIR, STORAGE_DIR
from app.return_review import REVIEW_DIR, record_once


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
                saved_index.setdefault(normalize_filename(saved_filename), set()).add(student_id)

            if student_id and original_filename:
                original_index.setdefault(normalize_filename(original_filename), set()).add(student_id)

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
    imported_zip_dir.mkdir(parents=True, exist_ok=True)
    stored_zip_path = unique_path(imported_zip_dir / f"{ts}__{sanitize_name(zip_file_path.name)}")
    shutil.move(str(zip_file_path), str(stored_zip_path))
    with stored_zip_path.open("rb") as source:
        digest = hashlib.sha256()
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    batch = f"{category}::{task_id}::{digest.hexdigest()}"
    saved, original = build_submission_indexes(category, task_id)
    matched_count = 0
    unmatched_files, review_ids = [], []
    with zipfile.ZipFile(stored_zip_path) as archive:
        for index, entry in enumerate(archive.infolist()):
            if entry.is_dir():
                continue
            filename = Path(entry.filename).name
            if filename in ("", ".", ".."):
                continue
            key = normalize_filename(filename)
            candidates = sorted(saved.get(key, set()) | original.get(key, set()))
            ticket = hashlib.sha256(f"{batch}::{index}".encode()).hexdigest()[:16]
            if len(candidates) == 1:
                directory = matched_dir / candidates[0] / ticket
            elif candidates:
                directory = corrected_root / "review" / ticket
            else:
                directory = unmatched_dir / ticket
            directory.mkdir(parents=True, exist_ok=True)
            path = directory / sanitize_name(filename)
            if not path.is_file():
                with NamedTemporaryFile(dir=directory, delete=False) as temp:
                    try:
                        with archive.open(entry) as src:
                            shutil.copyfileobj(src, temp)
                        temp.flush()
                        os.replace(temp.name, path)
                    finally:
                        Path(temp.name).unlink(missing_ok=True)
            if len(candidates) == 1:
                record_once(category, task_id, candidates[0], filename, path)
                matched_count += 1
            elif candidates:
                folder = REVIEW_DIR / ticket
                folder.mkdir(parents=True, exist_ok=True)
                item = dict(category=category, task_id=task_id, filename=filename,
                            path=str(path), candidates=candidates)
                tmp = folder / "review.tmp"
                tmp.write_text(json.dumps(item, ensure_ascii=False), encoding="utf-8")
                tmp.replace(folder / "review.json")
                if not (folder / "done").exists():
                    review_ids.append(ticket)
                else:
                    matched_count += 1
            else:
                unmatched_files.append(filename)
    return dict(stored_zip_path=stored_zip_path, matched_count=matched_count,
                unmatched_count=len(unmatched_files), unmatched_files=unmatched_files,
                review_count=len(review_ids))
