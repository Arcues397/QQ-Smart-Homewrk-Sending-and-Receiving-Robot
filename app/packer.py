import re
from pathlib import Path
from tempfile import mkdtemp
from zipfile import ZIP_DEFLATED, ZipFile

from app.archiver import sanitize_name
from app.config import ARCHIVE_DIR, EXPORT_DIR
from app.reports import load_latest_submissions
from app.rosters import expected_students


def assignment_title(task_id: str) -> str:
    match = re.fullmatch(r"(作业|实验|预习)(\d+)", task_id)
    if match:
        kind, number = match.groups()
        label = {"作业": "作业", "实验": "实验报告", "预习": "实验预习报告"}[kind]
        return f"第{number}次{label}"
    return sanitize_name(task_id)


def export_assignment_zip(category: str, task_id: str) -> Path:
    latest = load_latest_submissions(category, task_id)
    if not latest:
        raise ValueError("这个作业批次还没有提交记录。")

    valid_dir = ARCHIVE_DIR / sanitize_name(category) / sanitize_name(task_id) / "valid"
    files = []
    seen = set()
    for student_id, record in sorted(latest.items()):
        name = record["saved_filename"]
        if not name or Path(name).name != name or not name.lower().endswith(".pdf"):
            raise ValueError(f"学号 {student_id} 的归档文件名异常，请核对。")
        if name.casefold() in seen:
            raise ValueError("有不同学号对应同一份 PDF，请核对后再打包。")
        path = valid_dir / name
        if not path.is_file():
            raise FileNotFoundError(f"学号 {student_id} 的最新归档文件缺失。")
        seen.add(name.casefold())
        files.append(path)

    count, expected = len(files), len(expected_students(category, task_id))
    title = assignment_title(task_id)
    filename = f"格拉斯哥学院-电工五班-{title}-实交-{count}份（应交{expected}份）.zip"
    # 同一批次可反复导出，每次发送使用独立的文件。
    directory = Path(mkdtemp(prefix="pack-", dir=EXPORT_DIR))
    output = directory / filename
    try:
        with ZipFile(output, "x", ZIP_DEFLATED, compresslevel=1) as archive:
            for path in files:
                archive.write(path, arcname=path.name)
    except BaseException:
        output.unlink(missing_ok=True)
        directory.rmdir()
        raise
    return output
