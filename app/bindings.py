import csv
import os
from tempfile import NamedTemporaryFile

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


def check_binding(openid, student_id, bindings=None):
    if bindings is None:
        bindings = load_bindings()
    current = bindings.get(openid)
    if ((current and current["student_id"] != student_id)
            or any(key != openid and value["student_id"] == student_id
                   for key, value in bindings.items())):
        raise ValueError("绑定信息冲突。请发送「申请换绑 <学号> <姓名>」，由管理员核实。")


def save_bindings(bindings):
    with NamedTemporaryFile(mode="w", newline="", encoding="utf-8-sig",
                            dir=BINDINGS_FILE.parent, delete=False) as f:
        temp = f.name
        try:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()
            for key, value in bindings.items():
                writer.writerow({"openid": key, **value})
            f.flush()
            os.fsync(f.fileno())
            os.replace(temp, BINDINGS_FILE)
        finally:
            if os.path.exists(temp):
                os.unlink(temp)


def bind_openid(openid, student_id, name):
    bindings = load_bindings()
    check_binding(openid, student_id, bindings)
    value = {"student_id": student_id, "name": name}
    if bindings.get(openid) != value:
        bindings[openid] = value
        save_bindings(bindings)


def get_binding(openid):
    return load_bindings().get(openid)


def request_rebind(openid, student_id, name):
    import secrets
    from datetime import datetime
    import json
    from app.student_registry import validate_student

    if not validate_student(student_id, name)["ok"]:
        raise ValueError("请核对学号和姓名。")
    bindings = load_bindings()
    if bindings.get(openid, {}).get("student_id") == student_id:
        return "当前账号已绑定该学号。"
    directory = DATA_DIR / "rebind-requests"
    directory.mkdir(mode=0o700, exist_ok=True)
    ticket = secrets.token_hex(6)
    owners = sorted(key for key, value in bindings.items() if value["student_id"] == student_id)
    with (directory / ticket).open("x") as f:
        json.dump(dict(openid=openid, student_id=student_id, name=name,
                       previous=bindings.get(openid), owners=owners, time=datetime.now().timestamp()), f)
    return f"请把申请编号 {ticket} 和学号交给管理员核实身份。申请 24 小时内有效。"


def approve_rebind(ticket, student_id, name):
    import json
    import re
    import time
    from app.pending import clear_pending
    from app.student_registry import validate_student

    if not re.fullmatch(r"[a-f0-9]{12}", ticket):
        raise ValueError("换绑申请编号无效。")
    path = DATA_DIR / "rebind-requests" / ticket
    if not path.is_file():
        raise ValueError("申请不存在或已经处理。")
    request = json.loads(path.read_text())
    if time.time() - request["time"] >= 86400:
        raise ValueError("申请已过期，请学生重新申请。")
    if (request["student_id"], request["name"]) != (student_id, name) or not validate_student(student_id, name)["ok"]:
        raise ValueError("申请与核实的信息不符。")
    openid = request["openid"]
    bindings = load_bindings()
    owners = sorted(key for key, value in bindings.items() if value["student_id"] == student_id)
    if bindings.get(openid) != request["previous"] or owners != request["owners"]:
        raise ValueError("绑定信息已变更，请学生重新申请。")
    for key in owners:
        del bindings[key]
    bindings[openid] = {"student_id": student_id, "name": name}
    save_bindings(bindings)
    for key in [openid, *owners]:
        clear_pending(key)
    path.unlink()
    return f"已确认换绑：{student_id} {name}。"
