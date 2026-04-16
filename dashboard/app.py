"""
Harness 教学仪表盘 - 主入口
"""
import streamlit as st

st.set_page_config(
    page_title="Harness Agent 教学框架",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 侧边栏导航说明
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
st.sidebar.caption("参考 `PROGRESS.md` 了解当前进度")

# 主页内容
st.title("Harness Agent 教学框架")
st.markdown("""
> 从零复现类似 Claude Code 的极简 Coding Agent，
> 理解每个核心组件的工作原理。
""")

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("总步骤数", "12", "Step 0~11")
with col2:
    st.metric("当前阶段", "准备阶段", "Step 0")
with col3:
    st.metric("技术栈", "Python", "千问 API")

st.divider()
st.info("👈 使用左侧导航栏进入各个 Step 的详细页面")
