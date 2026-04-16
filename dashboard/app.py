"""
Harness 教学仪表盘 - 主入口
运行方式：streamlit run dashboard/app.py（从项目根目录执行）
"""
import streamlit as st
import pathlib
import re

st.set_page_config(
    page_title="Harness Agent 教学框架",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 项目根目录：dashboard/ 上一级
ROOT = pathlib.Path(__file__).parent.parent

# ── 读取当前进度 ────────────────────────────────────────────
current_stage = "准备阶段"
current_step = "Step 0"
done_count, total_count = 0, 1

progress_path = ROOT / "PROGRESS.md"
if progress_path.exists():
    raw = progress_path.read_text(encoding="utf-8")
    m_stage = re.search(r"\*\*当前阶段\*\*：(.+)", raw)
    m_step = re.search(r"\*\*当前步骤\*\*：(.+)", raw)
    if m_stage:
        current_stage = m_stage.group(1).strip()
    if m_step:
        current_step = m_step.group(1).strip().split(" — ")[0]
    total_count = raw.count("- [ ]") + raw.count("- [x]")
    done_count = raw.count("- [x]")

# ── 侧边栏 ─────────────────────────────────────────────────
st.sidebar.title("Harness Agent")
st.sidebar.caption("极简 Coding Agent 教学框架")
st.sidebar.divider()

st.sidebar.markdown("""
### 学习路径

| 阶段 | 步骤 |
|------|------|
| 准备 | Step 0 |
| 骨架 | Step 1-3 |
| 能力 | Step 4-6 |
| 体验 | Step 7-9 |
| 进阶 | Step 10-11 |
""")

st.sidebar.divider()
st.sidebar.progress(
    done_count / total_count if total_count else 0,
    text=f"总进度：{done_count}/{total_count} 子任务"
)

# ── 主页内容 ───────────────────────────────────────────────
st.title("Harness Agent 教学框架")
st.markdown("""
> 从零复现类似 Claude Code 的极简 Coding Agent，
> 理解每个核心组件的工作原理。
""")

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("总步骤数", "12", "Step 0~11")
with col2:
    st.metric("当前阶段", current_stage)
with col3:
    st.metric("当前步骤", current_step)

st.divider()
st.info("👈 使用左侧导航栏进入各个 Step 的详细页面")
