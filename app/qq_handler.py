import botpy
from botpy import logging
from botpy.message import C2CMessage

from app.config import APPID, APPSECRET, ADMIN_OPENID
from app.downloader import download_file, is_pdf_filename, check_pdf_header
from app.parser import (
    parse_submit_command,
    parse_pack_command,
    parse_import_return_command,
    parse_query_command,
)
from app.pending import set_pending, get_pending, clear_pending
from app.archiver import archive_submission
from app.assignment_config import get_assignment_config
from app.records import append_submission_record
from app.student_registry import validate_student
from app.packer import export_assignment_zip
from app.bindings import bind_openid, get_binding
from app.returns import find_return_file
from app.return_importer import import_return_zip
from app.file_sender import send_pdf_to_user

_log = logging.get_logger()

# 管理员导入返还 zip 的待处理状态
IMPORT_RETURN_PENDING = {}


def is_admin(openid: str) -> bool:
    return bool(ADMIN_OPENID) and openid == ADMIN_OPENID


def is_zip_filename(filename: str) -> bool:
    return filename.lower().endswith(".zip")


class MyClient(botpy.Client):
    async def on_ready(self):
        _log.info(f"robot 「{self.robot.name}」 on_ready!")

    async def on_c2c_message_create(self, message: C2CMessage):
        print("\n========== 收到 QQ 单聊 ==========")
        print(f"消息ID: {message.id}")
        print(f"内容: {message.content!r}")

        openid = message.author.user_openid
        print(f"openid: {openid}")

        attachments = getattr(message, "attachments", None)
        content = (message.content or "").strip()

        # 0. 管理员：/打包 <类别> <批次>
        pack_cmd = parse_pack_command(content)
        if pack_cmd:
            if not is_admin(openid):
                await message._api.post_c2c_message(
                    openid=openid,
                    msg_type=0,
                    msg_id=message.id,
                    content="你没有权限执行打包命令。"
                )
                print("非管理员尝试打包")
                print("========== 单聊结束 ==========\n")
                return

            try:
                export_path = export_assignment_zip(
                    category=pack_cmd["category"],
                    task_id=pack_cmd["task_id"]
                )
                await message._api.post_c2c_message(
                    openid=openid,
                    msg_type=0,
                    msg_id=message.id,
                    content=(
                        f"打包成功。\n"
                        f"作业：{pack_cmd['category']} / {pack_cmd['task_id']}\n"
                        f"压缩包：{export_path.name}\n"
                        f"位置：{export_path}"
                    )
                )
                print(f"已生成压缩包：{export_path}")
            except Exception as e:
                print(f"打包失败: {e}")
                await message._api.post_c2c_message(
                    openid=openid,
                    msg_type=0,
                    msg_id=message.id,
                    content=f"打包失败：{e}"
                )

            print("========== 单聊结束 ==========\n")
            return

        # 1. 管理员：/导入返还 <类别> <批次>
        import_return_cmd = parse_import_return_command(content)
        if import_return_cmd:
            if not is_admin(openid):
                await message._api.post_c2c_message(
                    openid=openid,
                    msg_type=0,
                    msg_id=message.id,
                    content="你没有权限执行导入返还命令。"
                )
                print("非管理员尝试导入返还")
                print("========== 单聊结束 ==========\n")
                return

            IMPORT_RETURN_PENDING[openid] = import_return_cmd

            await message._api.post_c2c_message(
                openid=openid,
                msg_type=0,
                msg_id=message.id,
                content=(
                    f"已记录返还导入信息：\n"
                    f"类别：{import_return_cmd['category']}\n"
                    f"批次：{import_return_cmd['task_id']}\n\n"
                    f"请发送老师返还的 zip 文件。"
                )
            )
            print("已记录导入返还待处理信息")
            print("========== 单聊结束 ==========\n")
            return

        # 2. 学生：查询 <类别> <批次>
        query_cmd = parse_query_command(content)
        if query_cmd:
            binding = get_binding(openid)
            if not binding:
                await message._api.post_c2c_message(
                    openid=openid,
                    msg_type=0,
                    msg_id=message.id,
                    content=(
                        "未找到你的身份绑定信息。\n"
                        "请先正常提交过一次作业后再查询。"
                    )
                )
                print("查询失败：无 binding")
                print("========== 单聊结束 ==========\n")
                return

            student_id = binding["student_id"]
            record = find_return_file(
                category=query_cmd["category"],
                task_id=query_cmd["task_id"],
                student_id=student_id,
            )

            if not record:
                await message._api.post_c2c_message(
                    openid=openid,
                    msg_type=0,
                    msg_id=message.id,
                    content=(
                        f"暂未找到你的返还文件：{query_cmd['category']} / {query_cmd['task_id']}"
                    )
                )
                print("查询完成：未找到返还文件")
                print("========== 单聊结束 ==========\n")
                return

            saved_path = record["saved_path"]

            try:
                await message._api.post_c2c_message(
                    openid=openid,
                    msg_type=0,
                    msg_id=message.id,
                    content=(
                        f"已找到你的返还文件，正在发送：\n"
                        f"{record['saved_filename']}"
                    )
                )

                await send_pdf_to_user(message, saved_path)

                print(f"已回传返还文件：{saved_path}")

            except Exception as e:
                print(f"回传返还文件失败: {e}")
                await message._api.post_c2c_message(
                    openid=openid,
                    msg_type=0,
                    msg_id=message.id,
                    content=f"找到文件了，但发送失败：{e}"
                )

            print("========== 单聊结束 ==========\n")
            return

        # 3. 学生：提交 <类别> <批次> <学号> <姓名>
        parsed = parse_submit_command(content)
        if parsed:
            cfg = get_assignment_config(parsed["category"], parsed["task_id"])
            if not cfg:
                await message._api.post_c2c_message(
                    openid=openid,
                    msg_type=0,
                    msg_id=message.id,
                    content=(
                        f"未找到这次作业的配置：{parsed['category']} / {parsed['task_id']}\n"
                        f"请联系管理员先录入该作业。"
                    )
                )
                print("作业配置不存在")
                print("========== 单聊结束 ==========\n")
                return

            student_check = validate_student(
                student_id=parsed["student_id"],
                name=parsed["name"]
            )

            if not student_check["ok"]:
                if student_check["reason"] == "student_id_not_found":
                    await message._api.post_c2c_message(
                        openid=openid,
                        msg_type=0,
                        msg_id=message.id,
                        content=(
                            f"学号校验失败：未找到学号 {parsed['student_id']}。\n"
                            f"请检查后重新发送。"
                        )
                    )
                elif student_check["reason"] == "name_mismatch":
                    await message._api.post_c2c_message(
                        openid=openid,
                        msg_type=0,
                        msg_id=message.id,
                        content=(
                            f"姓名与学号不匹配。\n"
                            f"学号 {parsed['student_id']} 对应姓名应为：{student_check['expected_name']}\n"
                            f"请检查后重新发送。"
                        )
                    )

                print("学号姓名校验失败")
                print("========== 单聊结束 ==========\n")
                return

            set_pending(openid, parsed)

            await message._api.post_c2c_message(
                openid=openid,
                msg_type=0,
                msg_id=message.id,
                content=(
                    f"已记录提交信息：\n"
                    f"类别：{parsed['category']}\n"
                    f"批次：{parsed['task_id']}\n"
                    f"学号：{parsed['student_id']}\n"
                    f"姓名：{parsed['name']}\n\n"
                    f"请在10分钟内发送PDF文件。"
                )
            )
            print("已记录待提交信息")
            print("========== 单聊结束 ==========\n")
            return

        # 4. 检测附件
        pdf_attachment = None
        zip_attachment = None

        if attachments:
            for att in attachments:
                filename = getattr(att, "filename", "") or ""
                if zip_attachment is None and is_zip_filename(filename):
                    zip_attachment = att
                if pdf_attachment is None and is_pdf_filename(filename):
                    pdf_attachment = att

        # 4A. 管理员导入返还 zip
        if zip_attachment:
            if is_admin(openid) and openid in IMPORT_RETURN_PENDING:
                pending_import = IMPORT_RETURN_PENDING[openid]

                try:
                    zip_path = await download_file(
                        url=zip_attachment.url,
                        filename=zip_attachment.filename
                    )

                    result = import_return_zip(
                        zip_file_path=zip_path,
                        category=pending_import["category"],
                        task_id=pending_import["task_id"],
                    )

                    IMPORT_RETURN_PENDING.pop(openid, None)

                    reply_text = (
                        f"返还 zip 导入成功。\n"
                        f"作业：{pending_import['category']} / {pending_import['task_id']}\n"
                        f"匹配成功：{result['matched_count']} 个\n"
                        f"未匹配：{result['unmatched_count']} 个"
                    )

                    if result["unmatched_files"]:
                        preview = "、".join(result["unmatched_files"][:5])
                        reply_text += f"\n未匹配示例：{preview}"

                    await message._api.post_c2c_message(
                        openid=openid,
                        msg_type=0,
                        msg_id=message.id,
                        content=reply_text
                    )

                    print(f"返还 zip 已导入：{result['stored_zip_path']}")
                    print(f"匹配成功：{result['matched_count']}")
                    print(f"未匹配：{result['unmatched_count']}")

                except Exception as e:
                    print(f"导入返还 zip 失败: {e}")
                    await message._api.post_c2c_message(
                        openid=openid,
                        msg_type=0,
                        msg_id=message.id,
                        content=f"导入返还 zip 失败：{e}"
                    )

                print("========== 单聊结束 ==========\n")
                return

        # 4B. 学生提交 PDF
        if pdf_attachment:
            pending = get_pending(openid)
            if not pending:
                await message._api.post_c2c_message(
                    openid=openid,
                    msg_type=0,
                    msg_id=message.id,
                    content=(
                        "检测到你发送了PDF，但没有找到有效的提交信息。\n"
                        "请先发送：提交 <类别> <批次> <学号> <姓名>"
                    )
                )
                print("收到PDF，但没有待提交记录")
                print("========== 单聊结束 ==========\n")
                return

            cfg = get_assignment_config(pending["category"], pending["task_id"])
            if not cfg:
                await message._api.post_c2c_message(
                    openid=openid,
                    msg_type=0,
                    msg_id=message.id,
                    content=(
                        f"当前作业配置不存在：{pending['category']} / {pending['task_id']}\n"
                        f"请联系管理员。"
                    )
                )
                print("待提交对应的作业配置不存在")
                print("========== 单聊结束 ==========\n")
                return

            try:
                save_path = await download_file(
                    url=pdf_attachment.url,
                    filename=pdf_attachment.filename
                )

                if not check_pdf_header(save_path):
                    save_path.unlink(missing_ok=True)
                    await message._api.post_c2c_message(
                        openid=openid,
                        msg_type=0,
                        msg_id=message.id,
                        content="下载完成，但文件不是合法PDF。"
                    )
                    print("PDF 文件头校验失败")
                    print("========== 单聊结束 ==========\n")
                    return

                archive_result = archive_submission(
                    downloaded_file=save_path,
                    category=pending["category"],
                    task_id=pending["task_id"],
                    student_id=pending["student_id"],
                    name=pending["name"],
                    filename_template=cfg["filename_template"],
                )

                final_path = archive_result["final_path"]
                duplicate_path = archive_result["duplicate_path"]
                replaced_old = archive_result["replaced_old"]

                append_submission_record(
                    openid=openid,
                    category=pending["category"],
                    task_id=pending["task_id"],
                    student_id=pending["student_id"],
                    name=pending["name"],
                    original_filename=pdf_attachment.filename,
                    saved_path=final_path,
                    replaced_old=replaced_old,
                    duplicate_path=duplicate_path,
                )

                bind_openid(
                    openid=openid,
                    student_id=pending["student_id"],
                    name=pending["name"],
                )

                clear_pending(openid)

                print(f"PDF 已归档到: {final_path}")
                print(f"是否替换旧版本: {replaced_old}")
                if duplicate_path:
                    print(f"旧版本已移到: {duplicate_path}")

                reply_text = (
                    f"提交成功。\n"
                    f"已归档到：{pending['category']}/{pending['task_id']}\n"
                    f"保存文件名：{final_path.name}"
                )

                if replaced_old:
                    reply_text += "\n检测到重复提交，旧版本已移入 duplicate 文件夹。"

                await message._api.post_c2c_message(
                    openid=openid,
                    msg_type=0,
                    msg_id=message.id,
                    content=reply_text
                )

            except Exception as e:
                print(f"处理PDF失败: {e}")
                await message._api.post_c2c_message(
                    openid=openid,
                    msg_type=0,
                    msg_id=message.id,
                    content=f"PDF处理失败：{e}"
                )

            print("========== 单聊结束 ==========\n")
            return

        # 5. 普通消息
        await message._api.post_c2c_message(
            openid=openid,
            msg_type=0,
            msg_id=message.id,
            content=(
                "未识别到有效操作。\n"
                "学生提交：提交 <类别> <批次> <学号> <姓名>\n"
                "学生查询：查询 <类别> <批次>\n"
                "管理员打包：/打包 <类别> <批次>\n"
                "管理员导入返还：/导入返还 <类别> <批次>"
            )
        )

        print("普通消息，未处理")
        print("========== 单聊结束 ==========\n")


def run_bot():
    intents = botpy.Intents(public_messages=True)
    client = MyClient(intents=intents)
    client.run(appid=APPID, secret=APPSECRET)