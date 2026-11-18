from functools import lru_cache
import openpyxl

from app.config import BASE_DIR


STUDENT_XLSX = BASE_DIR / "25电工五班学号对照(2).xlsx"


def load_students() -> dict[str, str]:
    stat = STUDENT_XLSX.stat()
    return _read_students((stat.st_ino, stat.st_mtime_ns, stat.st_size))


@lru_cache(maxsize=1)
def _read_students(version) -> dict[str, str]:
    wb = openpyxl.load_workbook(STUDENT_XLSX, data_only=True)
    ws = wb["Sheet1"]

    students = {}
    for row in ws.iter_rows(min_row=1, values_only=True):
        if not row:
            continue

        student_id = row[0] if len(row) > 0 else None
        name = row[1] if len(row) > 1 else None

        if student_id is None or name is None:
            continue

        sid = str(student_id).strip()
        sname = str(name).strip()

        if sid and sname:
            students[sid] = sname

    wb.close()
    return students


def validate_student(student_id: str, name: str):
    students = load_students()

    if student_id not in students:
        return {
            "ok": False,
            "reason": "student_id_not_found",
            "expected_name": None,
        }

    expected_name = students[student_id]
    if expected_name != name:
        return {
            "ok": False,
            "reason": "name_mismatch",
            "expected_name": expected_name,
        }

    return {
        "ok": True,
        "reason": "ok",
        "expected_name": expected_name,
    }