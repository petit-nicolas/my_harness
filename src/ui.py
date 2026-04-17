"""
Rich UI 工具集

提供终端侧流式打印 (StreamPrinter) 和 spinner 辅助，
供 cli.py 和需要终端富文本输出的场景使用。
"""
import sys
from contextlib import contextmanager

from rich.console import Console
from rich.live import Live
from rich.spinner import Spinner
from rich.text import Text

_console = Console()


# ── 流式文本打印器 ───────────────────────────────────────────

class StreamPrinter:
    """
    将流式 token 实时打印到终端。

    用法：
        printer = StreamPrinter()
        printer.start()                 # 显示前缀
        printer.write("hello ")         # 每个 chunk 调用一次
        printer.write("world")
        printer.finish()                # 换行并重置状态
    """

    def __init__(self, console: Console | None = None, prefix: str = "") -> None:
        self._console = console or _console
        self._prefix = prefix
        self._started = False

    def start(self) -> None:
        """打印行首前缀（如 'Harness  '）"""
        if not self._started:
            self._console.print(f"\n[bold green]{self._prefix}[/bold green]", end="  ")
            self._started = True

    def write(self, chunk: str) -> None:
        """将一个 token chunk 输出到终端"""
        if not self._started:
            self.start()
        # 直接写到 stdout，不经过 Rich 的 markup 解析，避免干扰
        sys.stdout.write(chunk)
        sys.stdout.flush()

    def finish(self) -> None:
        """结束流式输出，换行"""
        if self._started:
            sys.stdout.write("\n\n")
            sys.stdout.flush()
        self._started = False

    def make_chunk_callback(self):
        """
        返回一个可直接传给 run_agent(on_text_chunk=...) 的回调函数。
        首个 chunk 时自动调用 start()。
        """
        first = [True]

        def _cb(chunk: str) -> None:
            if first[0]:
                self.start()
                first[0] = False
            self.write(chunk)

        return _cb


# ── Spinner 上下文管理器 ─────────────────────────────────────

@contextmanager
def thinking_spinner(text: str = "思考中..."):
    """
    在工具调用期间显示 spinner，退出时自动清除。

    用法：
        with thinking_spinner():
            result = run_tool(...)
    """
    with Live(
        Spinner("dots", text=Text(text, style="dim")),
        console=_console,
        refresh_per_second=10,
        transient=True,   # 结束后清除 spinner 行
    ):
        yield


# ── 工具调用 / 结果打印 ──────────────────────────────────────

def print_tool_call_rich(console: Console, name: str, args: dict) -> None:
    args_str = ", ".join(f"{k}={repr(v)[:50]}" for k, v in args.items())
    console.print(f"  [yellow]⚙ {name}({args_str})[/yellow]")


def print_tool_result_rich(console: Console, name: str, result: str) -> None:
    preview = result[:150].replace("\n", " ")
    suffix = "..." if len(result) > 150 else ""
    console.print(f"  [dim]↳ {preview}{suffix}[/dim]")
