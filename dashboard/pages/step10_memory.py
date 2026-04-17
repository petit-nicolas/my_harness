"""
Step 10 — 记忆系统

展示内容：
1. 记忆库实时浏览（增删查）
2. 四大分类说明与使用场景
3. 记忆注入 system prompt 演示
4. /extract 自动提取原理与代码
"""
import pathlib
import sys

import streamlit as st

ROOT = pathlib.Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

st.set_page_config(page_title="Step 10 — 记忆系统", page_icon="🧠", layout="wide")
st.title("Step 10 · 记忆系统")
st.caption("跨会话长期记忆：让 agent 记住你的偏好、项目约定和历史反馈")

with st.expander("📋 学习目标", expanded=False):
    st.markdown("""
- 理解四类记忆（user / feedback / project / reference）的用途
- 掌握 `/remember`、`/memories`、`/forget`、`/extract` 命令
- 了解记忆如何注入 system prompt，影响 agent 行为
- 体验 LLM 自动从对话中提取记忆的过程
""")

tab1, tab2, tab3, tab4 = st.tabs([
    "🧠 记忆库",
    "🗂️ 分类说明",
    "🔧 Prompt 注入",
    "🔬 代码原理",
])

# ────────────────────────────────────────────────────────────
# Tab 1 — 记忆库实时浏览
# ────────────────────────────────────────────────────────────
with tab1:
    try:
        from src.memory import (
            load_memories, add_memory, delete_memory, search_memories,
            ALL_CATEGORIES, CATEGORY_DESC, memory_file_path,
        )
        mem_available = True
    except Exception as e:
        st.error(f"记忆模块加载失败：{e}")
        mem_available = False

    if mem_available:
        mfile = memory_file_path()
        st.caption(f"存储文件：`{mfile}`")

        col_left, col_right = st.columns([1, 1])

        # ── 左：添加记忆 ─────────────────────────────────
        with col_left:
            st.subheader("添加记忆")
            new_cat = st.selectbox("分类", ALL_CATEGORIES, format_func=lambda c: f"{c} — {CATEGORY_DESC[c]}")
            new_content = st.text_area("内容", placeholder="例如：用户不喜欢冗长解释，直接给代码")
            new_tags_raw = st.text_input("标签（空格分隔，无需加 #）", placeholder="style preference")

            if st.button("💾 保存记忆", use_container_width=True):
                if new_content.strip():
                    tags = [t.strip() for t in new_tags_raw.split() if t.strip()]
                    try:
                        entry = add_memory(new_content.strip(), category=new_cat, tags=tags)
                        st.success(f"已保存 [id:{entry.id}]")
                        st.rerun()
                    except Exception as e:
                        st.error(f"保存失败：{e}")
                else:
                    st.warning("内容不能为空")

        # ── 右：搜索框 ────────────────────────────────────
        with col_right:
            st.subheader("搜索记忆")
            query = st.text_input("关键词搜索", placeholder="输入关键词后回车…")
            filter_cat = st.selectbox("按分类过滤", ["全部"] + ALL_CATEGORIES)

        st.divider()

        # ── 记忆列表 ─────────────────────────────────────
        cat_filter = None if filter_cat == "全部" else filter_cat
        if query:
            memories = search_memories(query, category=cat_filter)
        else:
            memories = load_memories()
            if cat_filter:
                memories = [m for m in memories if m.category == cat_filter]

        if not memories:
            st.info("暂无记忆。在左侧添加第一条，或在 CLI 中使用 /remember 命令。")
        else:
            st.markdown(f"**共 {len(memories)} 条记忆**")
            for cat in ALL_CATEGORIES:
                cat_entries = [e for e in memories if e.category == cat]
                if not cat_entries:
                    continue
                cat_color = {"user": "🟦", "feedback": "🟧", "project": "🟩", "reference": "🟪"}.get(cat, "⬜")
                with st.expander(f"{cat_color} **{cat}** — {CATEGORY_DESC[cat]}（{len(cat_entries)} 条）", expanded=True):
                    for e in cat_entries:
                        c1, c2 = st.columns([9, 1])
                        tag_str = "  " + "  ".join(f"`#{t}`" for t in e.tags) if e.tags else ""
                        src_badge = " 🤖" if e.source == "auto" else ""
                        c1.markdown(f"**[{e.id}]**{src_badge} {e.content}{tag_str}  \n<small>{e.created_at}</small>", unsafe_allow_html=True)
                        if c2.button("🗑", key="del_" + e.id, help="删除此条记忆"):
                            delete_memory(e.id)
                            st.rerun()

# ────────────────────────────────────────────────────────────
# Tab 2 — 分类说明
# ────────────────────────────────────────────────────────────
with tab2:
    st.subheader("四大记忆分类")

    categories_detail = {
        "user": {
            "icon": "🟦",
            "desc": "用户个人偏好、习惯、背景",
            "examples": [
                "用户叫 Tom，后端工程师，偏好 Python",
                "用户不喜欢过多注释，代码要简洁",
                "用户习惯 TDD，希望先写测试",
            ],
            "cmd": "/remember user 用户不喜欢过多注释 #style",
        },
        "feedback": {
            "icon": "🟧",
            "desc": "用户对 agent 行为的正/负反馈",
            "examples": [
                "用户反馈：解释太长，直接给结论",
                "用户喜欢 diff 格式展示代码改动",
                "用户不希望 agent 主动重构无关函数",
            ],
            "cmd": "/remember feedback 解释太长，直接给结论 #communication",
        },
        "project": {
            "icon": "🟩",
            "desc": "特定项目的技术栈、路径、约定",
            "examples": [
                "/Users/tom/api 使用 FastAPI + SQLModel",
                "测试命令：pytest -x --tb=short",
                "提交前必须跑 ruff check .",
            ],
            "cmd": "/remember project /Users/tom/api 使用 FastAPI #fastapi",
        },
        "reference": {
            "icon": "🟪",
            "desc": "通用技术知识、最佳实践",
            "examples": [
                "Python 3.10+ 用 X | Y 替代 Optional[X]",
                "Docker 多阶段构建可显著减小镜像体积",
                "SQLAlchemy 2.0 Session 要显式 commit",
            ],
            "cmd": "/remember reference Python 3.10+ 用 X | Y 替代 Optional[X] #python",
        },
    }

    for cat, info in categories_detail.items():
        with st.expander(f"{info['icon']} **{cat}** — {info['desc']}", expanded=True):
            col1, col2 = st.columns([1, 1])
            with col1:
                st.markdown("**典型内容**")
                for ex in info["examples"]:
                    st.markdown(f"- {ex}")
            with col2:
                st.markdown("**CLI 示例**")
                st.code(info["cmd"], language="bash")

    st.divider()
    st.markdown("""
**设计原则**

| 原则 | 说明 |
|------|------|
| 分类不严格 | 分类只是提示，记错了可以删了重加 |
| 内容要具体 | "用户喜欢简洁" < "用户不喜欢在每个函数里加注释" |
| 用 #tag 辅助 | tag 支持搜索过滤，建议统一命名约定 |
| 自动 vs 手动 | /extract 批量提取，/remember 精确控制 |
""")

# ────────────────────────────────────────────────────────────
# Tab 3 — Prompt 注入演示
# ────────────────────────────────────────────────────────────
with tab3:
    st.subheader("记忆如何注入 system prompt")

    st.markdown("记忆在每次对话开始时自动读取并注入到 system prompt 的 `{{memories}}` 占位符：")

    col1, col2 = st.columns([1, 1])
    with col1:
        st.markdown("**MEMORY.md（存储格式）**")
        st.code("""## user
- [2026-04-17] [id:abc123] 用户偏好简洁风格 #style
- [2026-04-17] [id:def456] [auto] 用户叫 Tom #name

## project
- [2026-04-17] [id:ghi789] 使用 FastAPI #fastapi

## feedback
<!-- 暂无记录 -->

## reference
<!-- 暂无记录 -->""", language="markdown")

    with col2:
        st.markdown("**注入后的 system prompt 片段**")
        st.code("""## 长期记忆（跨会话积累）

### user（用户个人偏好、习惯、背景信息）
- 用户偏好简洁风格  #style
- 用户叫 Tom  #name

### project（具体项目的技术栈、约定、路径）
- 使用 FastAPI  #fastapi""", language="markdown")

    st.divider()

    # 实时 prompt 预览
    st.subheader("实时 Prompt 预览")
    if st.button("🔍 生成当前 system prompt（含记忆）"):
        try:
            from src.prompt import build_system_prompt
            prompt = build_system_prompt()
            if "长期记忆" in prompt:
                st.success("✅ 记忆已成功注入 system prompt")
            else:
                st.info("ℹ️ 当前记忆库为空，无注入内容")
            with st.expander("查看完整 system prompt"):
                st.text(prompt)
        except Exception as e:
            st.error(f"生成失败：{e}")

    st.markdown("""
**注入位置设计**

```
系统提示词结构（system_prompt.md）：
  # 角色定义
  ## 工作原则
  ## 工具使用规范
  ## 长结果处理原则
  ## 输出规范
  ## 运行环境（cwd / date / os / shell）
  ## Git 上下文           ← {{git_context}}
  ## 长期记忆              ← {{memories}}   ← 在这里
  ## 项目约定（CLAUDE.md）← {{claude_md}}
```

记忆注入在 git 上下文之后、项目约定之前，属于"持久化上下文"层。
""")

# ────────────────────────────────────────────────────────────
# Tab 4 — 代码原理
# ────────────────────────────────────────────────────────────
with tab4:
    st.subheader("核心实现")

    st.markdown("#### `src/memory.py` — MemoryEntry 与 MEMORY.md 读写")
    st.code("""
@dataclass
class MemoryEntry:
    id: str           # 6位随机字母数字
    category: str     # user | feedback | project | reference
    content: str
    created_at: str   # YYYY-MM-DD
    tags: list[str]
    source: str       # "manual" | "auto"

    def to_line(self) -> str:
        tag_str = " " + " ".join(f"#{t}" for t in self.tags) if self.tags else ""
        src_hint = " [auto]" if self.source == "auto" else ""
        return f"- [{self.created_at}] [id:{self.id}]{src_hint} {self.content}{tag_str}"
""", language="python")

    st.markdown("#### `/extract` — LLM 自动提取")
    st.code("""
def _extract_memories_from_session(session: AgentSession) -> None:
    history_text = "\\n".join(
        f"[{m['role']}] {str(m.get('content', ''))[:500]}"
        for m in session.messages[-20:]
        if m["role"] in ("user", "assistant")
    )
    extract_prompt = (
        "从以下对话中提取值得长期记住的事实，格式：\\n"
        "每行一条：[category] <内容>（可附 #tag）\\n"
        "category 只能是：user / feedback / project / reference\\n"
        f"\\n=== 对话内容 ===\\n{history_text}"
    )
    resp = chat([{"role": "user", "content": extract_prompt}], stream=False)
    # 解析响应，每行 [category] content #tags → add_memory(...)
""", language="python")

    st.markdown("#### `src/prompt.py` — 记忆注入")
    st.code("""
def load_memories_context() -> str:
    entries = load_memories()           # 读 ~/.harness/memory/MEMORY.md
    return format_for_prompt(entries)   # 格式化为 Markdown 块

def build_system_prompt(cwd=None) -> str:
    ...
    replacements = {
        "{{memories}}": load_memories_context(),  # ← 注入点
        ...
    }
""", language="python")

    st.divider()
    st.markdown("""
**架构对比：Claude Code vs Harness**

| 特性 | Claude Code | Harness |
|------|-------------|---------|
| 存储格式 | `~/.claude/CLAUDE.md` | `~/.harness/memory/MEMORY.md` |
| 分类 | 无明确分类 | 4 类：user/feedback/project/reference |
| 自动提取 | 无（手动维护） | `/extract` LLM 提取 |
| 项目级记忆 | `CLAUDE.md` 放项目根 | project 类 + `{{claude_md}}` 双重支持 |
| 注入位置 | system prompt 末尾 | system prompt 中间（git 上下文之后） |
""")
