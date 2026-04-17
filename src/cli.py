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
    console.print(
        f"[dim]  耗时 {elapsed:.1f}s  ·  "
        f"prompt {u.prompt_tokens}  completion {u.completion_tokens}  "
        f"total {u.total}[/dim]"
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
    "/help":    "显示所有可用命令",
    "/clear":   "清空当前对话历史",
    "/cost":    "显示本次会话 Token 用量",
    "/compact": "压缩对话历史（保留最近 6 条，其余用摘要替换）",
    "/exit":    "退出 Harness",
}

def handle_command(cmd: str, session: AgentSession) -> bool:
    """
    处理 / 开头的内置命令。
    返回 True 表示已处理，False 表示不是内置命令。
    """
    cmd = cmd.strip()
    if cmd == "/help":
        for name, desc in COMMANDS.items():
            console.print(f"  [cyan]{name:<10}[/cyan] {desc}")
        return True
    if cmd == "/clear":
        session.messages.clear()
        clear_result_cache()
        console.print("[dim]对话历史 + 工具结果缓存已清空[/dim]")
        return True
    if cmd == "/cost":
        u = session.usage
        console.print(
            f"  prompt {u.prompt_tokens}  "
            f"completion {u.completion_tokens}  "
            f"total {u.total}"
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

    # stop_event：Ctrl+C 时置位，通知 run_agent 中断当前任务
    stop_event = threading.Event()
    agent_running = False

    def handle_sigint(sig, frame):
        nonlocal agent_running
        if agent_running:
            stop_event.set()
            console.print("\n[dim]正在中断...[/dim]")
        else:
            console.print("\n[dim]Bye.[/dim]")
            sys.exit(0)

    signal.signal(signal.SIGINT, handle_sigint)

    while True:
        try:
            user_input = input("\n> ").strip()
        except EOFError:
            console.print("\n[dim]Bye.[/dim]")
            break

        if not user_input:
            continue

        if handle_command(user_input, session):
            continue

        # 重置中断信号
        stop_event.clear()
        agent_running = True
        t0 = time.time()

        # 每轮对话创建一个新的流式打印器
        printer = StreamPrinter(console, prefix="Harness")

        try:
            run_agent(
                session=session,
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
            print_cost(session, time.time() - t0)

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
    args = parser.parse_args()

    confirm_fn = make_confirm_fn(yolo=args.yolo)
    session = AgentSession(cwd=args.cwd)

    if args.prompt:
        run_once(args.prompt, confirm_fn=confirm_fn)
    else:
        repl(session, confirm_fn=confirm_fn)
