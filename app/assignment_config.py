import json

from app.config import DATA_DIR


ASSIGNMENTS_FILE = DATA_DIR / "assignments.json"


def make_assignment_key(category: str, task_id: str) -> str:
    return f"{category}::{task_id}"


def load_assignments() -> dict:
    if not ASSIGNMENTS_FILE.exists():
        return {}

    with open(ASSIGNMENTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def get_assignment_config(category: str, task_id: str):
    data = load_assignments()
    key = make_assignment_key(category, task_id)
    return data.get(key)