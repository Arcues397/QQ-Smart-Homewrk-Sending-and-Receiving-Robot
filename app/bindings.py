import csv

from app.config import DATA_DIR


BINDINGS_FILE = DATA_DIR / "bindings.csv"
FIELDNAMES = ["openid", "student_id", "name"]


def ensure_bindings_file():
    if not BINDINGS_FILE.exists():
        with open(BINDINGS_FILE, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()


def load_bindings() -> dict[str, dict]:
    ensure_bindings_file()

    bindings = {}
    with open(BINDINGS_FILE, "r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            openid = (row.get("openid") or "").strip()
            if openid:
                bindings[openid] = {
                    "student_id": (row.get("student_id") or "").strip(),
                    "name": (row.get("name") or "").strip(),
                }
    return bindings


def bind_openid(openid: str, student_id: str, name: str):
    ensure_bindings_file()
    bindings = load_bindings()

    bindings[openid] = {
        "student_id": student_id,
        "name": name,
    }

    with open(BINDINGS_FILE, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for k, v in bindings.items():
            writer.writerow({
                "openid": k,
                "student_id": v["student_id"],
                "name": v["name"],
            })


def get_binding(openid: str):
    bindings = load_bindings()
    return bindings.get(openid)