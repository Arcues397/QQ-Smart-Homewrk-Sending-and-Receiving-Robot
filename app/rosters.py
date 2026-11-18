import json
import sqlite3
from contextlib import closing
from functools import lru_cache

from app.config import DATA_DIR
from app.student_registry import load_students

DATABASE = DATA_DIR / "assignment-rosters.sqlite3"


@lru_cache(maxsize=1)
def snapshot_batches(keys: tuple[str, ...]):
    with closing(sqlite3.connect(DATABASE)) as db, db:
        db.execute("CREATE TABLE IF NOT EXISTS rosters (batch TEXT PRIMARY KEY, students TEXT NOT NULL)")
        known = {key for key, in db.execute("SELECT batch FROM rosters")}
        missing = [key for key in keys if key not in known]
        if missing:
            students = load_students()
            if not students:
                raise ValueError("班级名单为空，无法保存应交名单。")
            roster = json.dumps(students, ensure_ascii=False)
            db.executemany("INSERT OR IGNORE INTO rosters VALUES (?, ?)", [(key, roster) for key in missing])


def expected_students(category, task_id):
    from app.assignment_config import get_assignment_config, make_assignment_key
    if not get_assignment_config(category, task_id):
        raise ValueError("未找到这个作业批次。")
    with closing(sqlite3.connect(DATABASE)) as db:
        row = db.execute("SELECT students FROM rosters WHERE batch = ?",
                         (make_assignment_key(category, task_id),)).fetchone()
    return json.loads(row[0])
