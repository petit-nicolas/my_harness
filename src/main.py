"""Harness Agent 入口文件"""
import sys


def main() -> None:
    """根据当前实现阶段选择入口"""
    try:
        from src.cli import run_cli
        run_cli()
    except ImportError:
        # cli.py 在 Step 3.4 实现，当前阶段直接提示
        print("CLI 尚未实现（Step 3.4），请运行各阶段的独立测试脚本。")
        sys.exit(0)


if __name__ == "__main__":
    main()
