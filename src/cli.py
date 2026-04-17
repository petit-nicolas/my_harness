"""
CLI 界面 — REPL 交互入口

功能：
- 基于 readline 的多轮对话 REPL
- --prompt "..." 单次执行模式（适合脚本调用）
- Ctrl+C 双级处理：运行中中断任务，空闲时退出
- /help /clear /cost 内置命令
- rich 彩色输出：用户蓝色、工具黄色、结果灰色、错误红色
"""
import argparse
import os
import readline  # 激活后 input() 自动支持方向键历史
import signal
import sys
import threading
import time

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from src.agent import AgentSession, run_agent, compact_context, estimate_tokens
from src.memory import (
    add_memory, delete_memory, load_memories, search_memories,
    format_for_prompt, ALL_CATEGORIES, CATEGORY_DESC, memory_file_path,
)
from src.session import save_session, load_session, list_sessions, delete_session, sessions_dir
from src.tools import clear_result_cache
from src.ui import StreamPrinter, print_tool_call_rich, print_tool_result_rich

console = Console()

# ── 颜色输出工具 ────────────────────────────────────────────

def print_user(text: str) -> None:
    console.print(f"[bold blue]你[/bold blue]  {text}")

def print_agent(text: str) -> None:
    """非流式模式的完整回复打印（兼容 Streamlit 测试）"""
    console.print(f"\n[bold green]Harness[/bold green]  {text}\n")

def print_tool_call(name: str, args: dict) -> None:
    print_tool_call_rich(console, name, args)

def print_tool_result(name: str, result: str) -> None:
    print_tool_result_rich(console, name, result)

def print_error(text: str) -> None:
    console.print(f"[bold red]错误[/bold red]  {text}")

def print_cost(session: AgentSession, elapsed: float) -> None:
    u = session.usage
    est = estimate_tokens(session.messages)
    console.print(
        f"[dim]  耗时 {elapsed:.1f}s  ·  "
        f"prompt {u.prompt_tokens}  completion {u.completion_tokens}  "
        f"total {u.total}  (历史估算 {est} tokens)[/dim]"
    )

# ── 安全确认回调 ─────────────────────────────────────────────

def make_confirm_fn(yolo: bool):
    """
    构造 confirm_fn 回调。

    yolo=True  → 返回 None，agent.py 跳过所有安全检查
    yolo=False → 返回交互式 y/n 确认函数
    """
    if yolo:
        return None  # None 告知 run_agent 跳过安全检查

    def confirm(tool_name: str, reason: str, arguments: dict) -> bool:
        # 构造简短的操作描述
        if tool_name == "run_shell":
            target = arguments.get("command", "")[:80]
        else:
            target = arguments.get("path", "")

        console.print(
            f"\n  [bold yellow]⚠ 危险操作[/bold yellow]  {reason}\n"
            f"  [dim]工具[/dim] {tool_name}  [dim]目标[/dim] {target}"
        )
        try:
            answer = input("  继续执行？[y/N] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            answer = "n"
        return answer in ("y", "yes")

    return confirm

# ── 内置命令 ────────────────────────────────────────────────

COMMANDS = {
    "/help":              "显示所有可用命令",
    "/clear":             "清空当前对话历史",
    "/cost":              "显示本次会话 Token 用量",
    "/compact":           "压缩对话历史（保留最近 6 条，其余用摘要替换）",
    "/save":              "保存当前会话到磁盘",
    "/sessions":          "列出最近保存的历史会话",
    "/load <id>":         "恢复指定会话（id 来自 /sessions）",
    "/remember [cat] <text>": "记住一条信息（cat: user/feedback/project/reference）",
    "/memories [query]":  "浏览或搜索记忆库",
    "/forget <id>":       "删除指定记忆（id 来自 /memories）",
    "/extract":           "让 LLM 从当前对话中自动提取记忆",
    "/exit":              "退出 Harness",
}

def handle_command(cmd: str, session: AgentSession, session_box: list | None = None) -> bool:
    """
    处理 / 开头的内置命令。
    返回 True 表示已处理，False 表示不是内置命令。

    session_box: [session] 列表容器，允许 /load 替换 REPL 当前 session。
    """
    cmd = cmd.strip()
    if cmd == "/help":
        for name, desc in COMMANDS.items():
            console.print(f"  [cyan]{name:<16}[/cyan] {desc}")
        return True
    if cmd == "/clear":
        session.messages.clear()
        clear_result_cache()
        console.print("[dim]对话历史 + 工具结果缓存已清空[/dim]")
        return True
    if cmd == "/cost":
        u = session.usage
        est = estimate_tokens(session.messages)
        console.print(
            f"\n  [bold]Token 用量[/bold]\n"
            f"  [dim]累计 prompt[/dim]   {u.prompt_tokens}\n"
            f"  [dim]累计 completion[/dim]{u.completion_tokens}\n"
            f"  [dim]API 累计 total[/dim] {u.total}\n"
            f"  [dim]历史估算 tokens[/dim]{est}   "
            f"[dim](消息数 {len(session.messages)})[/dim]\n"
        )
        return True
    if cmd == "/compact":
        msg_count = len(session.messages)
        est_tokens = estimate_tokens(session.messages)
        console.print(f"[dim]  当前消息数：{msg_count}  估算 token：{est_tokens}[/dim]")
        if msg_count == 0:
            console.print("[dim]  对话历史为空，无需压缩[/dim]")
            return True
        with console.status("[dim]正在生成摘要...[/dim]", spinner="dots"):
            summary = compact_context(session)
        console.print(f"[dim]  压缩完成，剩余消息数：{len(session.messages)}[/dim]")
        console.print(f"[dim]  摘要预览：{summary[:100]}...[/dim]" if len(summary) > 100 else f"[dim]  摘要：{summary}[/dim]")
        return True
    if cmd == "/save":
        if not session.messages:
            console.print("[dim]  对话历史为空，无需保存[/dim]")
            return True
        try:
            sid = save_session(session)
            console.print(f"[dim]  已保存 → {sid}[/dim]")
            console.print(f"[dim]  路径：{sessions_dir() / (sid + '.json')}[/dim]")
        except Exception as e:
            console.print(f"[bold red]保存失败[/bold red]  {e}")
        return True
    if cmd == "/sessions":
        sessions = list_sessions(limit=10)
        if not sessions:
            console.print("[dim]  暂无历史会话[/dim]")
        else:
            console.print(f"  [dim]最近 {len(sessions)} 条会话（--resume <id> 可恢复）[/dim]")
            for s in sessions:
                console.print(
                    f"  [cyan]{s['id']}[/cyan]"
                    f"  [dim]{s['msg_count']} 条消息"
                    f"  {s['total_tokens']} tokens"
                    f"  {s['cwd']}[/dim]"
                )
        return True
    if cmd.startswith("/load"):
        parts = cmd.split(maxsplit=1)
        if len(parts) < 2:
            console.print("[dim]  用法：/load <session_id>[/dim]")
            return True
        sid = parts[1].strip()
        try:
            new_session = load_session(sid)
            if session_box is not None:
                session_box[0] = new_session
                clear_result_cache()
                console.print(f"[dim]  已恢复会话 {sid}（{len(new_session.messages)} 条消息）[/dim]")
            else:
                console.print("[dim]  /load 仅在 REPL 模式下可用[/dim]")
        except Exception as e:
            console.print(f"[bold red]加载失败[/bold red]  {e}")
        return True
    # ── 记忆系统命令 ─────────────────────────────────────────
    if cmd.startswith("/remember"):
        parts = cmd.split(maxsplit=2)
        # /remember <text>  或  /remember <category> <text>
        if len(parts) < 2:
            console.print("[dim]  用法：/remember [user|feedback|project|reference] <内容>[/dim]")
            return True
        # 判断第一个参数是否是分类名
        if len(parts) >= 3 and parts[1] in ALL_CATEGORIES:
            cat, content = parts[1], parts[2]
        else:
            cat = "user"
            content = " ".join(parts[1:])
        # 简单提取行内 #tag
        import re as _re
        tags = _re.findall(r"#(\w+)", content)
        content_clean = _re.sub(r"\s*#\w+", "", content).strip()
        try:
            entry = add_memory(content_clean, category=cat, tags=tags)
            console.print(
                f"[dim]  记忆已保存[/dim]  [{cat}] [id:{entry.id}] {content_clean}"
            )
        except Exception as e:
            console.print(f"[bold red]保存失败[/bold red]  {e}")
        return True

    if cmd.startswith("/memories"):
        parts = cmd.split(maxsplit=1)
        query = parts[1].strip() if len(parts) > 1 else ""
        memories = search_memories(query) if query else load_memories()
        if not memories:
            hint = f"无匹配 {query!r}" if query else "记忆库为空，用 /remember 添加"
            console.print(f"[dim]  {hint}[/dim]")
            console.print(f"[dim]  文件：{memory_file_path()}[/dim]")
        else:
            console.print(f"[dim]  {len(memories)} 条记忆（/forget <id> 删除）[/dim]")
            for cat in ALL_CATEGORIES:
                cat_entries = [e for e in memories if e.category == cat]
                if not cat_entries:
                    continue
                console.print(f"  [bold cyan]{cat}[/bold cyan]  [dim]{CATEGORY_DESC[cat]}[/dim]")
                for e in cat_entries:
                    tag_str = "  " + " ".join(f"#{ t}" for t in e.tags) if e.tags else ""
                    console.print(f"    [dim][id:{e.id}][/dim] {e.content}{tag_str}")
        return True

    if cmd.startswith("/forget"):
        parts = cmd.split(maxsplit=1)
        if len(parts) < 2:
            console.print("[dim]  用法：/forget <memory_id>[/dim]")
            return True
        mid = parts[1].strip()
        if delete_memory(mid):
            console.print(f"[dim]  已删除记忆 {mid}[/dim]")
        else:
            console.print(f"[bold red]未找到[/bold red]  id={mid}")
        return True

    if cmd == "/extract":
        if not session.messages:
            console.print("[dim]  当前对话为空，无法提取[/dim]")
            return True
        _extract_memories_from_session(session)
        return True

    if cmd in ("/exit", "/quit"):
        console.print("[dim]Bye.[/dim]")
        sys.exit(0)
    return False

# ── REPL 主循环 ─────────────────────────────────────────────

def repl(session: AgentSession, confirm_fn=None) -> None:
    """多轮交互 REPL"""
    yolo_hint = "  [bold red]⚡ YOLO 模式：跳过所有安全检查[/bold red]\n" if confirm_fn is None else ""
    console.print(Panel.fit(
        "[bold]Harness[/bold]  极简 Coding Agent\n"
        + yolo_hint +
        "[dim]输入 /help 查看命令，Ctrl+C 中断当前任务，再次 Ctrl+C 退出[/dim]",
        border_style="blue",
    ))

    # session_box 允许 /load 命令替换当前 session
    session_box: list[AgentSession] = [session]

    # stop_event：Ctrl+C 时置位，通知 run_agent 中断当前任务
    stop_event = threading.Event()
    agent_running = False

    def handle_sigint(sig, frame):
        nonlocal agent_running
        if agent_running:
            stop_event.set()
            console.print("\n[dim]正在中断...[/dim]")
        else:
            # 退出前自动保存非空会话
            cur = session_box[0]
            if cur.messages:
                try:
                    sid = save_session(cur)
                    console.print(f"\n[dim]已自动保存会话 → {sid}[/dim]")
                except Exception:
                    pass
            console.print("[dim]Bye.[/dim]")
            sys.exit(0)

    signal.signal(signal.SIGINT, handle_sigint)

    while True:
        cur = session_box[0]
        try:
            user_input = input("\n> ").strip()
        except EOFError:
            if cur.messages:
                try:
                    sid = save_session(cur)
                    console.print(f"\n[dim]已自动保存会话 → {sid}[/dim]")
                except Exception:
                    pass
            console.print("\n[dim]Bye.[/dim]")
            break

        if not user_input:
            continue

        if handle_command(user_input, cur, session_box=session_box):
            continue

        # 重置中断信号
        stop_event.clear()
        agent_running = True
        t0 = time.time()

        # 每轮对话创建一个新的流式打印器
        printer = StreamPrinter(console, prefix="Harness")

        try:
            run_agent(
                session=session_box[0],
                user_input=user_input,
                stream=True,
                on_text_chunk=printer.make_chunk_callback(),
                on_text=lambda _: printer.finish(),
                on_tool_call=print_tool_call,
                on_tool_result=print_tool_result,
                confirm_fn=confirm_fn,
                stop_event=stop_event,
            )
        except Exception as e:
            print_error(str(e))
        finally:
            agent_running = False
            print_cost(session_box[0], time.time() - t0)

# ── 单次执行模式 ────────────────────────────────────────────

def run_once(prompt: str, confirm_fn=None) -> None:
    """--prompt 模式：执行一次后退出"""
    session = AgentSession()
    print_user(prompt)
    t0 = time.time()
    printer = StreamPrinter(console, prefix="Harness")
    try:
        run_agent(
            session=session,
            user_input=prompt,
            stream=True,
            on_text_chunk=printer.make_chunk_callback(),
            on_text=lambda _: printer.finish(),
            on_tool_call=print_tool_call,
            on_tool_result=print_tool_result,
            confirm_fn=confirm_fn,
        )
    except Exception as e:
        print_error(str(e))
        sys.exit(1)
    print_cost(session, time.time() - t0)

# ── LLM 自动记忆提取 ─────────────────────────────────────────

def _extract_memories_from_session(session: AgentSession) -> None:
    """
    让 LLM 从当前对话中提取值得记住的事实，写入记忆库。
    通过 /extract 命令触发，不会自动调用（避免额外 API 消耗）。
    """
    from src.client import chat

    # 构造提取提示
    history_text = "\n".join(
        f"[{m['role']}] {str(m.get('content', ''))[:500]}"
        for m in session.messages[-20:]   # 只看最近 20 条
        if m["role"] in ("user", "assistant")
    )
    if not history_text.strip():
        console.print("[dim]  没有可分析的对话内容[/dim]")
        return

    extract_prompt = (
        "从以下对话中提取值得长期记住的事实，格式：\n"
        "每行一条，格式：[category] <内容>（可附 #tag）\n"
        "category 只能是：user / feedback / project / reference\n"
        "只提取有明确信息量的条目，无关紧要的细节忽略。\n"
        "如果没有值得记忆的内容，回复：无\n\n"
        f"=== 对话内容 ===\n{history_text}\n=== 结束 ===\n"
    )

    msgs = [{"role": "user", "content": extract_prompt}]
    with console.status("[dim]正在从对话中提取记忆...[/dim]", spinner="dots"):
        resp = chat(msgs, stream=False)

    text = (resp.choices[0].message.content or "").strip()
    if not text or text.strip() == "无":
        console.print("[dim]  未发现值得记忆的内容[/dim]")
        return

    import re as _re
    saved = 0
    for line in text.splitlines():
        line = line.strip().lstrip("-•* ")
        m = _re.match(r"\[(user|feedback|project|reference)\]\s+(.+)", line)
        if not m:
            continue
        cat, content = m.group(1), m.group(2).strip()
        tags = _re.findall(r"#(\w+)", content)
        content_clean = _re.sub(r"\s*#\w+", "", content).strip()
        if content_clean:
            entry = add_memory(content_clean, category=cat, tags=tags, source="auto")
            console.print(f"[dim]  → [{cat}] [id:{entry.id}] {content_clean}[/dim]")
            saved += 1

    if saved:
        console.print(f"[dim]  共提取 {saved} 条记忆并保存[/dim]")
    else:
        console.print("[dim]  未能解析出有效记忆条目[/dim]")


# ── 入口 ────────────────────────────────────────────────────

def run_cli() -> None:
    parser = argparse.ArgumentParser(
        prog="harness",
        description="Harness — 极简 Coding Agent",
    )
    parser.add_argument(
        "--prompt", "-p",
        metavar="TEXT",
        help="单次执行模式：发送一条消息后退出",
    )
    parser.add_argument(
        "--cwd",
        metavar="DIR",
        help="指定工作目录（默认为当前目录）",
        default=os.getcwd(),
    )
    parser.add_argument(
        "--yolo",
        action="store_true",
        help="跳过所有危险操作确认（谨慎使用）",
    )
    parser.add_argument(
        "--resume",
        metavar="SESSION_ID",
        help="恢复指定历史会话（ID 来自 /sessions 命令）",
    )
    parser.add_argument(
        "--sessions",
        action="store_true",
        help="列出最近的历史会话后退出",
    )
    args = parser.parse_args()

    # --sessions 只列表不进 REPL
    if args.sessions:
        sessions = list_sessions(limit=20)
        if not sessions:
            console.print("[dim]暂无历史会话[/dim]")
        else:
            console.print(f"[dim]最近 {len(sessions)} 条会话（--resume <id> 可恢复）[/dim]\n")
            for s in sessions:
                console.print(
                    f"  [cyan]{s['id']}[/cyan]"
                    f"  [dim]{s['msg_count']} 条消息"
                    f"  {s['total_tokens']} tokens"
                    f"  {s['cwd']}[/dim]"
                )
        return

    confirm_fn = make_confirm_fn(yolo=args.yolo)

    # --resume 恢复历史会话
    if args.resume:
        try:
            session = load_session(args.resume)
            console.print(f"[dim]已恢复会话 {args.resume}（{len(session.messages)} 条消息）[/dim]")
        except Exception as e:
            console.print(f"[bold red]恢复失败[/bold red]  {e}")
            sys.exit(1)
    else:
        session = AgentSession(cwd=args.cwd)

    if args.prompt:
        run_once(args.prompt, confirm_fn=confirm_fn)
    else:
        repl(session, confirm_fn=confirm_fn)
