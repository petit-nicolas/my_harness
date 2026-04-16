"""共享 UI 组件"""
import streamlit as st


def step_header(step_num: int, title: str, stage: str, caption: str = "") -> None:
    """每个 Step 页面的标准页头"""
    st.title(f"Step {step_num} · {title}")
    st.caption(f"{stage} — {caption}")
    st.divider()


def learning_goals(goals: list[str]) -> None:
    """学习目标区块"""
    st.header("学习目标")
    for g in goals:
        st.markdown(f"- {g}")


def key_code(title: str, code: str, language: str = "python") -> None:
    """关键代码展示区块"""
    st.subheader(title)
    st.code(code, language=language)
