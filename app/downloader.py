from pathlib import Path
import re
import httpx

from app.config import INBOX_DIR


def sanitize_filename(filename: str) -> str:
    """
    处理 Windows 不允许的文件名字符
    """
    filename = filename.strip()
    filename = re.sub(r'[\\/:*?"<>|]', "_", filename)
    return filename


def is_pdf_filename(filename: str) -> bool:
    return filename.lower().endswith(".pdf")


async def download_file(url: str, filename: str) -> Path:
    """
    下载文件到 storage/inbox
    """
    safe_name = sanitize_filename(filename)
    save_path = INBOX_DIR / safe_name

    async with httpx.AsyncClient(follow_redirects=True, timeout=60.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()

        with open(save_path, "wb") as f:
            f.write(resp.content)

    return save_path


def check_pdf_header(file_path: Path) -> bool:
    """
    检查是不是合法 PDF 文件头
    """
    try:
        with open(file_path, "rb") as f:
            header = f.read(5)
        return header == b"%PDF-"
    except Exception:
        return False