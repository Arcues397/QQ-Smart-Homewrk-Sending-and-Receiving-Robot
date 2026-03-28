import re


def parse_submit_command(content: str):
    if not content:
        return None

    content = content.strip()
    m = re.match(r"^提交\s+(\S+)\s+(\S+)\s+(\d{8,20})\s+(\S+)$", content)
    if not m:
        return None

    category, task_id, student_id, name = m.groups()
    return {
        "category": category,
        "task_id": task_id,
        "student_id": student_id,
        "name": name,
    }


def parse_pack_command(content: str):
    if not content:
        return None

    content = content.strip()
    m = re.match(r"^/打包\s+(\S+)\s+(\S+)$", content)
    if not m:
        return None

    category, task_id = m.groups()
    return {
        "category": category,
        "task_id": task_id,
    }


def parse_import_return_command(content: str):
    if not content:
        return None

    content = content.strip()
    m = re.match(r"^/导入返还\s+(\S+)\s+(\S+)$", content)
    if not m:
        return None

    category, task_id = m.groups()
    return {
        "category": category,
        "task_id": task_id,
    }


def parse_query_command(content: str):
    if not content:
        return None

    content = content.strip()
    m = re.match(r"^查询\s+(\S+)\s+(\S+)$", content)
    if not m:
        return None

    category, task_id = m.groups()
    return {
        "category": category,
        "task_id": task_id,
    }


def parse_submitted_command(content: str):
    if not content:
        return None

    content = content.strip()
    m = re.match(r"^/已交\s+(\S+)\s+(\S+)$", content)
    if not m:
        return None

    category, task_id = m.groups()
    return {
        "category": category,
        "task_id": task_id,
    }


def parse_missing_command(content: str):
    if not content:
        return None

    content = content.strip()
    m = re.match(r"^/缺交\s+(\S+)\s+(\S+)$", content)
    if not m:
        return None

    category, task_id = m.groups()
    return {
        "category": category,
        "task_id": task_id,
    }