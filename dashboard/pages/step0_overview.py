"""
Step 0 — 项目概览页
展示整体计划结构、技术架构图、当前进度
"""
import streamlit as st
import pathlib
import re

st.title("Step 0 · 项目概览")
st.caption("准备阶段 — 项目规则、骨架与仪表盘框架")

# ── 学习目标 ──────────────────────────────────────────────
st.header("学习目标")
st.markdown("""
1. 理解 Harness 项目的整体架构与 12 步学习路径
2. 掌握项目管理工具：Cursor 规则、进度追踪、Git 封版机制
3. 了解 Streamlit 如何作为每个 Step 的可视化配套工具
""")

# ── 整体架构图 ─────────────────────────────────────────────
st.header("整体架构")
st.markdown("""
```
用户输入 → 提示词编排 → Agent 循环 → 工具执行 → 结果输出 → 等待/退出
                                    ↑___________________________|
```
""")

col1, col2 = st.columns(2)

with col1:
    st.subheader("阶段分布")
    st.markdown("""
| 阶段 | 步骤 | 核心目标 |
|------|------|----------|
| 准备 | Step 0 | 基础设施 |
| 骨架 | Step 1-3 | 跑通 Agent 循环 |
| 能力 | Step 4-6 | 工具 + 安全 |
| 体验 | Step 7-9 | 流式 + 会话 |
| 进阶 | Step 10-11 | 记忆 + Hooks |
""")

with col2:
    st.subheader("技术栈")
    st.markdown("""
| 类别 | 选型 |
|------|------|
| 语言 | Python 3.11+ |
| 大模型 | 阿里千问 qwen-plus |
| SDK | openai（兼容模式）|
| 终端 UI | rich |
| 仪表盘 | streamlit |
""")

# ── 当前进度 ───────────────────────────────────────────────
st.header("当前进度")

progress_path = pathlib.Path(__file__).parent.parent / "PROGRESS.md"
if progress_path.exists():
    raw = progress_path.read_text(encoding="utf-8")

    # 提取当前状态块
    match = re.search(r"## 当前状态\n(.*?)---", raw, re.DOTALL)
    if match:
        st.markdown(match.group(1).strip())

    # 统计完成情况
    total = raw.count("- [ ]") + raw.count("- [x]")
    done = raw.count("- [x]")
    st.progress(done / total if total else 0, text=f"已完成 {done} / {total} 个子任务")
else:
    st.warning("未找到 PROGRESS.md，请确认项目根目录正确")

# ── 目录结构 ───────────────────────────────────────────────
st.header("项目目录结构")
st.code("""
harness/
├── .cursor/rules/          # Cursor 项目规则（3 份）
├── src/                    # Agent 核心代码（逐步填充）
├── dashboard/              # 本仪表盘
├── res/                    # 12 份 Claude Code 研究文档
├── PLAN.md                 # 完整实施计划
├── PROGRESS.md             # 进度追踪
├── requirements.txt        # Python 依赖
└── CLAUDE.md               # 项目上下文
""", language="text")

# ── 关键文件 ───────────────────────────────────────────────
st.header("关键文件速览")

tab1, tab2, tab3 = st.tabs(["PLAN.md", "PROGRESS.md", ".cursor/rules"])

with tab1:
    plan_path = pathlib.Path(__file__).parent.parent / "PLAN.md"
    if plan_path.exists():
        text = plan_path.read_text(encoding="utf-8")
        st.markdown(text[:3000] + "\n\n...（截取前 3000 字）")

with tab2:
    if progress_path.exists():
        st.markdown(progress_path.read_text(encoding="utf-8"))

with tab3:
    rules_dir = pathlib.Path(__file__).parent.parent / ".cursor" / "rules"
    for rule_file in sorted(rules_dir.glob("*.mdc")):
        with st.expander(rule_file.name):
            st.markdown(rule_file.read_text(encoding="utf-8"))
