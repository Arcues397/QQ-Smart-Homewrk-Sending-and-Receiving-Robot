from pathlib import Path

from app.assignment_config import get_assignment_config, load_assignments
from app.bindings import approve_rebind, get_binding, request_rebind
from app.file_sender import send_file_to_user
from app.pending import get_pending
from app.reports import generate_missing_report, generate_submitted_report, load_latest_submissions
from app.return_review import confirm_review, read_review, review_list
from app.rosters import expected_students


USAGE = {
    "帮助": "", "我的绑定": "", "作业列表": "[类别]", "提交格式": "<类别> <批次>",
    "查提交": "<类别> <批次>", "申请换绑": "<学号> <姓名>",
    "/已交": "<类别> <批次>", "/缺交": "<类别> <批次>",
    "/待确认": "<类别> <批次> [页码]", "/查看返还": "<返还编号>",
    "/确认返还": "<返还编号> <学号>", "/确认换绑": "<申请编号> <学号> <姓名>",
}


def help_text(admin):
    text = ("作业列表 [类别]\n提交格式 <类别> <批次>\n提交 <类别> <批次> <学号> <姓名>，随后发送 PDF"
            "\n查提交 <类别> <批次>\n查询 <类别> <批次>（领取批改文件）"
            "\n我的绑定\n申请换绑 <学号> <姓名>")
    if admin:
        extra = [f"{cmd} {args}" for cmd, args in USAGE.items() if cmd.startswith("/")]
        text += "\n管理员命令\n" + "\n".join(extra + ["/打包 <类别> <批次>", "/导入返还 <类别> <批次>"])
    return text


def command_result(cmd, args, openid, admin):
    if cmd.startswith("/") and not admin:
        raise ValueError("此命令仅供管理员使用。")
    usage = USAGE[cmd]
    required = usage.count("<")
    if not required <= len(args) <= required + usage.count("["):
        raise ValueError(f"用法：{cmd} {usage}".rstrip())
    if cmd == "帮助":
        return help_text(admin), None
    if cmd == "作业列表":
        keys = [key.split("::", 1) for key in load_assignments()]
        if not args:
            return "作业类别：" + "、".join(dict.fromkeys(c for c, t in keys)) + "\n发送 作业列表 <类别> 查看批次。", None
        tasks = [t for c, t in keys if c == args[0]]
        if not tasks:
            raise ValueError("未找到该类别。发送「作业列表」查看可用类别。")
        return f"{args[0]}：" + "、".join(tasks), None
    if cmd == "申请换绑":
        return request_rebind(openid, *args), None
    if cmd == "/确认换绑":
        return approve_rebind(*args), None
    if cmd == "/确认返还":
        return confirm_review(*args), None
    if cmd == "/查看返还":
        item = read_review(args[0])
        return f"{item['filename']}\n候选学号：{'、'.join(item['candidates'])}", Path(item['path'])
    binding = get_binding(openid)
    if cmd == "我的绑定":
        return (f"当前绑定：{binding['student_id']} {binding['name']}" if binding else "当前账号尚未绑定。"), None
    category, task = args[:2]
    if not get_assignment_config(category, task):
        raise ValueError("未找到该作业。发送「作业列表」核对类别和批次。")
    if cmd == "提交格式":
        identity = f"{binding['student_id']} {binding['name']}" if binding else "<学号> <姓名>"
        return f"提交 {category} {task} {identity}", None
    if cmd == "/待确认":
        items = review_list(category, task)
        if not items:
            return "该批次没有待确认的返还文件。", None
        page = args[2] if len(args) > 2 else "1"
        pages = (len(items) + 4) // 5
        if not page.isascii() or not page.isdigit() or len(page)>6 or not 1 <= int(page) <= pages:
            raise ValueError(f"页码范围：1 至 {pages}。")
        start = (int(page)-1)*5
        return f"待确认 {len(items)} 份，第 {page}/{pages} 页\n" + "\n".join(items[start:start+5]), None

    latest = load_latest_submissions(category, task)
    if cmd == "查提交":
        pending = get_pending(openid)
        waiting = pending and (pending["category"], pending["task_id"]) == (category, task)
        if not binding:
            return ("已收到提交信息，正在等待 PDF。" if waiting else "尚未绑定。首次成功提交 PDF 后可查询个人记录。"), None
        row = latest.get(binding["student_id"])
        status = (f"已交：{row['submit_time']}\n{row['saved_filename']}" if row else "尚无成功提交记录。")
        if waiting:
            status += "\n有一份提交正在等待 PDF。"
        return f"{category} / {task}\n{status}", None

    roster = expected_students(category, task)
    if cmd == "/缺交":
        report = generate_missing_report(category, task)
        names = [roster[s] for s in sorted(roster.keys() - latest.keys())]
        title = "缺交"
    else:
        report = generate_submitted_report(category, task)
        names = [latest[s]["name"] for s in sorted(latest)]
        title = "已交"
    text = f"{category} / {task}\n应交 {len(roster)} 人，{title} {len(names)} 人。"
    outside = latest.keys() - roster.keys()
    if outside:
        text += f" 另有 {len(outside)} 位应交名单外的学生提交，已计入实交。"
    return text + ("\n" + "、".join(names) if names else ""), report["path"]


async def handle_command(message, content, openid, admin):
    words = content.split()
    if not words or words[0] not in USAGE:
        return False
    async def reply(text, sequence=1):
        return await message._api.post_c2c_message(openid=openid, msg_type=0, msg_id=message.id,
                                                    msg_seq=sequence, content=text)
    try:
        text, file = command_result(words[0], words[1:], openid, admin)
    except ValueError as exc:
        await reply(str(exc))
        return True
    except Exception:
        import logging
        logging.exception("处理机器人命令失败")
        await reply("处理失败，请稍后重试。")
        return True
    await reply(text)
    if file:
        try:
            await send_file_to_user(message, file)
        except Exception:
            import logging
            logging.exception("发送命令附件失败")
            await reply("附件发送失败，请稍后重试。", 3)
    return True
