"""
Step 2 — 提示词编排页
可视化体验：系统提示词模板 + 动态组装过程 + 各组件分拆展示
"""
import sys
import pathlib

ROOT = pathlib.Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st
from src.prompt import build_system_prompt, get_git_context, load_claude_md

st.title("Step 2 · 提示词编排系统")
st.caption("骨架阶段 — 理解系统提示词如何从模板动态组装为完整上下文")

# ── 学习目标 ──────────────────────────────────────────────
with st.expander("学习目标", expanded=False):
    st.markdown("""
1. **模板机制**：系统提示词用占位符分离静态结构与动态数据
2. **环境感知**：cwd、日期、平台、Shell 让 agent 知道自己在哪里运行
3. **项目上下文**：git 信息和 CLAUDE.md 让 agent 理解正在工作的代码库
4. **组装原则**：所有上下文都来自 `cwd`，Harness 自身不污染目标项目的上下文
""")

st.divider()

# ── 控制面板 ──────────────────────────────────────────────
st.subheader("控制面板")

col1, col2 = st.columns([2, 1])
with col1:
    target_cwd = st.text_input(
        "目标项目目录（cwd）",
        value=str(ROOT),
        help="模拟 Harness 在哪个项目里运行，git 上下文和 CLAUDE.md 均来自该目录",
    )
with col2:
    st.markdown("<br>", unsafe_allow_html=True)
    run_btn = st.button("组装提示词", type="primary", use_container_width=True)

st.divider()

# ── 主体：模板 vs 组装结果 ──────────────────────────────────
tab_template, tab_assembled, tab_components = st.tabs(
    ["模板原文", "组装结果", "各组件拆解"]
)

with tab_template:
    st.markdown("**`src/system_prompt.md` 原始模板**（带占位符）")
    template_path = ROOT / "src" / "system_prompt.md"
    if template_path.exists():
        st.code(template_path.read_text(encoding="utf-8"), language="markdown")
    st.caption("占位符在组装时被真实运行时信息替换")

with tab_assembled:
    if run_btn:
        cwd_path = pathlib.Path(target_cwd)
        if not cwd_path.exists():
            st.error(f"目录不存在：{target_cwd}")
        else:
            with st.spinner("组装中..."):
                prompt = build_system_prompt(target_cwd)

            st.success(f"组装完成，共 {len(prompt)} 字符")
            st.markdown("**组装后的完整系统提示词：**")
            st.markdown(f"```\n{prompt}\n```")
    else:
        st.info("点击「组装提示词」查看结果")

with tab_components:
    if run_btn:
        cwd_path = pathlib.Path(target_cwd)
        if cwd_path.exists():
            st.markdown("#### 各占位符替换值")

            import os, platform
            from datetime import datetime

            components = {
                "{{cwd}}": target_cwd,
                "{{date}}": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "{{platform}}": platform.system(),
                "{{shell}}": os.environ.get("SHELL", "unknown"),
            }

            for k, v in components.items():
                with st.expander(f"`{k}` → `{v}`", expanded=False):
                    st.code(v)

            # git 上下文
            git_ctx = get_git_context(target_cwd)
            with st.expander(
                f"`{{{{git_context}}}}` → {'有内容' if git_ctx else '空（非 git 仓库）'}",
                expanded=bool(git_ctx),
            ):
                if git_ctx:
                    st.markdown(git_ctx)
                else:
                    st.caption(f"{target_cwd} 不是 git 仓库，此占位符替换为空字符串")

            # CLAUDE.md
            claude_md = load_claude_md(target_cwd)
            with st.expander(
                f"`{{{{claude_md}}}}` → {'找到 CLAUDE.md' if claude_md else '未找到 CLAUDE.md'}",
                expanded=bool(claude_md),
            ):
                if claude_md:
                    st.markdown(claude_md)
                else:
                    st.caption(f"从 {target_cwd} 向上递归 5 层，未找到 CLAUDE.md")
    else:
        st.info("点击「组装提示词」查看各组件拆解")

st.divider()

# ── 核心代码展示 ───────────────────────────────────────────
with st.expander("核心代码：src/prompt.py"):
    prompt_path = ROOT / "src" / "prompt.py"
    if prompt_path.exists():
        st.code(prompt_path.read_text(encoding="utf-8"), language="python")
