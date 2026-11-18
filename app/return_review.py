import csv
import json
import re
from pathlib import Path

from app.config import DATA_DIR
from app.returns import RETURNS_FILE, append_return_record

REVIEW_DIR = DATA_DIR / "return-review"


def read_review(ticket):
    if not re.fullmatch(r"[a-f0-9]{16}", ticket):
        raise ValueError("返还编号无效。")
    path = REVIEW_DIR / ticket / "review.json"
    if not path.is_file():
        raise ValueError("未找到这份待确认文件。")
    return json.loads(path.read_text(encoding="utf-8"))


def review_list(category, task_id):
    results = []
    for manifest in sorted(REVIEW_DIR.glob("*/review.json")):
        item = read_review(manifest.parent.name)
        if (item["category"], item["task_id"]) == (category, task_id) and not (manifest.parent / "done").exists():
            results.append(f"{manifest.parent.name} {item['filename']}\n候选学号：{'、'.join(item['candidates'])}")
    return results


def record_once(category, task_id, student_id, filename, path):
    if RETURNS_FILE.exists():
        with RETURNS_FILE.open(newline="", encoding="utf-8-sig") as f:
            if any(row["saved_path"] == str(path) for row in csv.DictReader(f)):
                return
    append_return_record(category, task_id, student_id, filename, path)


def confirm_review(ticket, student_id):
    item = read_review(ticket)
    if student_id not in item["candidates"]:
        raise ValueError("学号不在这份文件的候选名单中。")
    directory = REVIEW_DIR / ticket
    decision = directory / "student"
    if decision.exists() and decision.read_text() != student_id:
        raise ValueError("这份文件已经确认给其他学号。")
    path = Path(item["path"])
    if not path.is_file():
        raise ValueError("待确认文件缺失。")
    if not decision.exists():
        decision.write_text(student_id)
    record_once(item["category"], item["task_id"], student_id, item["filename"], path)
    (directory / "done").touch()
    return f"已确认返还 {item['filename']} 给 {student_id}。"
