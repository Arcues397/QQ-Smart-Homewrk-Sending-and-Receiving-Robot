import base64
from pathlib import Path


async def send_file_to_user(message, file_path: str | Path):
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"文件不存在：{file_path}")

    with open(file_path, "rb") as f:
        file_b64 = base64.b64encode(f.read()).decode("utf-8")

    upload_media = await message._api.post_c2c_file(
        openid=message.author.user_openid,
        file_type=4,
        file_data=file_b64,
        srv_send_msg=False,
    )

    await message._api.post_c2c_message(
        openid=message.author.user_openid,
        msg_type=7,
        msg_id=message.id,
        media=upload_media,
    )


async def send_pdf_to_user(message, file_path: str | Path):
    await send_file_to_user(message, file_path)