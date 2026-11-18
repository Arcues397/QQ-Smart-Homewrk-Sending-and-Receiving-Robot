import asyncio
import hashlib
import json
from pathlib import Path

import httpx
from botpy.http import Route


async def send_file_to_user(message, file_path: str | Path):
    """Upload a named file with QQ's chunked C2C file API."""
    path = Path(file_path)
    openid = message.author.user_openid

    async def request(action, payload):
        route = Route("POST", f"/v2/users/{{openid}}/{action}", openid=openid)
        result = await message._api._http.request(route, json=payload)
        if result is None:
            raise RuntimeError("QQ 文件接口未响应，请重试。")
        if isinstance(result, str):
            result = json.loads(result) if result else {}
        if result.get("code") or result.get("biz_code"):
            raise RuntimeError(f"QQ 文件接口返回 {result}")
        return result

    size = path.stat().st_size
    hashes = await asyncio.to_thread(file_hashes, path)
    plan = await request("upload_prepare", {
        "file_type": 4, "file_name": path.name, "file_size": size, **hashes,
    })
    upload_id = plan["upload_id"]
    block = int(plan["block_size"])
    parts = sorted(plan["parts"], key=lambda part: int(part["index"]))
    if block <= 0 or len(parts) != (size + block - 1) // block:
        raise RuntimeError("QQ 返回的文件分片数量异常，请重试。")
    async with httpx.AsyncClient(timeout=60) as client:
        with path.open("rb") as source:
            for index, part in enumerate(parts, 1):
                if int(part["index"]) != index:
                    raise RuntimeError("QQ 返回的文件分片序号异常，请重试。")
                data = source.read(block)
                try:
                    response = await client.put(part["presigned_url"], content=data)
                except httpx.RequestError:
                    raise RuntimeError("QQ 文件分片传输中断，请重试。") from None
                if not response.is_success:
                    raise RuntimeError(f"QQ 文件分片上传失败（HTTP {response.status_code}）。")
                finish = dict(upload_id=upload_id, part_index=index,
                              block_size=len(data), md5=hashlib.md5(data).hexdigest())
                for attempt in range(4):
                    try:
                        await request("upload_part_finish", finish)
                        break
                    except Exception as exc:
                        if "40093001" not in str(exc) or attempt == 3:
                            raise
                        await asyncio.sleep(1 + attempt)
    media = await request("files", {"upload_id": upload_id})
    await message._api.post_c2c_message(
        openid=openid, msg_type=7, msg_id=message.id, msg_seq=2,
        media={"file_info": media["file_info"]},
    )


def file_hashes(path: Path) -> dict[str, str]:
    md5, sha1, prefix = hashlib.md5(), hashlib.sha1(), hashlib.md5()
    remaining = 10_002_432  # QQ md5_10m prefix size in bytes
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            md5.update(chunk)
            sha1.update(chunk)
            if remaining:
                prefix.update(chunk[:remaining])
                remaining -= min(remaining, len(chunk))
    return dict(md5=md5.hexdigest(), sha1=sha1.hexdigest(), md5_10m=prefix.hexdigest())
