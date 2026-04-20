"""phy_1_wiki — Physics Wiki 浏览 / 反向链接 / log 状态机三栏视图（V1.7）

运行方式：
    streamlit run dashboard/app.py           # 然后从侧边栏选 "phy_1_wiki"
    streamlit run dashboard/pages/phy_1_wiki.py   # 单页直启

设计定位（只读）：
- 本页 **不触发任何写操作**（不做 wiki_write、也不做 wiki_index(rebuild=True)）
- 所有数据来自 `src/phy/wiki.py` 的只读接口 + 直接读 res/phy/wiki/log.md
- 目的：让 Builder 一眼掌握 wiki 当前状态；让用户验证 V1 闭环（schema+四工具+mineru）已打通

三大视图：
1. **总览**：统计卡片 + 学科分布 + Level 分布
2. **页面浏览**：按学科挑页 → 正文 + frontmatter + 反向链接
3. **log 状态机三栏**：active / paused / done（ingest 条目主视角，feedback 与 lint 折叠）
4. **Feedback Inbox**：扫 wiki/feedback/inbox/ 列出未处理 tickets
"""
from __future__ import annotations

import pathlib
import re
import sys
from dataclasses import dataclass

import streamlit as st

# 让 src.* 可导入：dashboard/pages/phy_1_wiki.py → 上溯两级到仓库根
ROOT = pathlib.Path(__file__).parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.phy import wiki  # noqa: E402


# ---------------------------------------------------------------------------
# 页面配置
# ---------------------------------------------------------------------------

WIKI_ROOT = ROOT / "res/phy/wiki"
LOG_PATH = WIKI_ROOT / "log.md"
INBOX_DIR = WIKI_ROOT / "feedback/inbox"

st.title("Physics Wiki · V1 基础设施仪表盘")
st.caption("V1.7 · 只读视图 · 数据源：`src/phy/wiki.py` + `res/phy/wiki/log.md`")


# ---------------------------------------------------------------------------
# 总览卡片
# ---------------------------------------------------------------------------

def _render_overview() -> None:
    if not WIKI_ROOT.exists():
        st.error(f"Wiki 根目录不存在 → {WIKI_ROOT}")
        return

    report = wiki.wiki_index()  # 只扫描、不写盘

    def _num(pattern: str, default: int = 0) -> int:
        m = re.search(pattern, report)
        return int(m.group(1)) if m else default

    concept_cnt = _num(r"概念页总数:\s*(\d+)")
    sources_cnt = _num(r"资料摘要页总数:\s*(\d+)")
    backlink_cnt = _num(r"反向链接总数:\s*(\d+)")
    broken_cnt = _num(r"断裂链接数:\s*(\d+)")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("概念页", concept_cnt)
    with c2:
        st.metric("资料摘要页", sources_cnt)
    with c3:
        st.metric("反向链接", backlink_cnt)
    with c4:
        delta = None
        if broken_cnt > 0:
            delta = f"-{broken_cnt} 待修"
        st.metric("断裂链接", broken_cnt, delta=delta, delta_color="inverse")

    st.divider()

    sub_col, lv_col = st.columns(2)
    with sub_col:
        st.subheader("学科分布")
        subj_block = _extract_section(report, "## 学科分布", "## Level 分布")
        if subj_block.strip():
            st.markdown(subj_block)
        else:
            st.caption("_（空）_")

    with lv_col:
        st.subheader("Level 分布")
        lvl_block = _extract_section(report, "## Level 分布", "## 断裂链接")
        if not lvl_block.strip():
            lvl_block = _extract_section(report, "## Level 分布", None)
        if lvl_block.strip():
            st.markdown(lvl_block)
        else:
            st.caption("_（空）_")

    if broken_cnt > 0:
        with st.expander(f"断裂链接（{broken_cnt}）— 点开查看", expanded=False):
            broken_block = _extract_section(report, "## 断裂链接（前 20 条）", None)
            if broken_block.strip():
                st.markdown(broken_block)


def _extract_section(text: str, start_marker: str, end_marker: str | None) -> str:
    """从 wiki_index 报告中抠出 [start_marker, end_marker) 区段内容（不含 marker 行）。"""
    if start_marker not in text:
        return ""
    idx = text.index(start_marker) + len(start_marker)
    if end_marker and end_marker in text[idx:]:
        end = idx + text[idx:].index(end_marker)
        return text[idx:end].strip()
    return text[idx:].strip()


# ---------------------------------------------------------------------------
# 页面浏览器
# ---------------------------------------------------------------------------

def _collect_all_pages() -> list[tuple[str, str, str]]:
    """返回 [(page_id, subject, title), ...]，按 subject 然后 page_id 排序。"""
    pages: list[tuple[str, str, str]] = []
    for path in wiki._iter_wiki_files():  # 含 meta + sources
        page_id = wiki._path_to_id(path)
        page = wiki._load_page(page_id)
        if page is None:
            continue
        subj = page.subject or "(unknown)"
        pages.append((page_id, subj, page.title))
    pages.sort(key=lambda x: (x[1], x[0]))
    return pages


def _render_browser() -> None:
    pages = _collect_all_pages()
    if not pages:
        st.info("Wiki 尚无任何页面。等 V2 ingest 启动后本页将填满。")
        return

    subj_to_pages: dict[str, list[tuple[str, str]]] = {}
    for pid, subj, title in pages:
        subj_to_pages.setdefault(subj, []).append((pid, title))

    left, right = st.columns([1, 2])

    with left:
        st.subheader(f"页面（{len(pages)}）")
        subj_options = sorted(subj_to_pages.keys())
        selected_subj = st.selectbox("筛选学科", ["全部"] + subj_options)

        candidates = (
            pages
            if selected_subj == "全部"
            else [(p, s, t) for (p, s, t) in pages if s == selected_subj]
        )
        page_id_options = [pid for pid, _, _ in candidates]
        page_labels = {pid: f"{pid}  —  {title}" for pid, _, title in candidates}

        if not page_id_options:
            st.caption("_（空）_")
            return

        selected_pid = st.radio(
            "选择页面",
            page_id_options,
            format_func=lambda pid: page_labels[pid],
            label_visibility="collapsed",
        )

    with right:
        if not selected_pid:
            return
        _render_page_detail(selected_pid)


def _render_page_detail(page_id: str) -> None:
    text = wiki.wiki_read(page_id)
    if text.startswith("错误"):
        st.error(text)
        return

    fm, body = wiki._parse_frontmatter(text)

    st.subheader(f"{page_id}")
    if fm:
        meta_cols = st.columns(4)
        field_order = ["title", "level", "subject", "updated"]
        for i, key in enumerate(field_order):
            val = fm.get(key, "—")
            with meta_cols[i]:
                st.caption(key)
                st.markdown(f"**{val}**")

        with st.expander("完整 frontmatter", expanded=False):
            st.json(
                {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in fm.items()}
            )

    st.markdown("##### 正文")
    with st.container(border=True):
        st.markdown(body)

    _render_backlinks(page_id)


def _render_backlinks(page_id: str) -> None:
    """反向链接：在 wiki 中搜谁引用了本页。"""
    inbound: list[tuple[str, str]] = []  # (src_page_id, snippet)
    for path in wiki._iter_wiki_files():
        src_id = wiki._path_to_id(path)
        if src_id == page_id:
            continue
        src_page = wiki._load_page(src_id)
        if src_page is None:
            continue
        if page_id in src_page.wikilinks():
            # 抠一小段上下文
            m = re.search(
                r"(.{0,60})\[\[" + re.escape(page_id) + r"(?:\|[^\]]+)?\]\](.{0,60})",
                src_page.body,
            )
            ctx = (m.group(0) if m else "").replace("\n", " ⏎ ")
            inbound.append((src_id, ctx))

    st.markdown(f"##### 反向链接（{len(inbound)}）")
    if not inbound:
        st.caption("_（暂无引用）_")
        return
    for src_id, ctx in inbound:
        st.markdown(f"- **{src_id}** · `{ctx}`")


# ---------------------------------------------------------------------------
# log 状态机三栏
# ---------------------------------------------------------------------------

@dataclass
class LogEntry:
    title: str         # "[2026-04-19] schema-init | 初始化 wiki 三件套"
    kind: str          # ingest / feedback / lint / schema-init / unknown
    state: str         # active / paused / done / unknown
    body: str          # 条目全文
    is_example: bool   # 标题是否以 "[示例]" 开头


RE_LOG_HEADER = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
RE_STATE_FIELD = re.compile(r"^-\s*\*\*state\*\*:\s*([a-zA-Z\-]+)", re.MULTILINE)


def _parse_log() -> list[LogEntry]:
    if not LOG_PATH.exists():
        return []
    text = LOG_PATH.read_text(encoding="utf-8")

    # 去掉 frontmatter
    _, body = wiki._parse_frontmatter(text) if text.startswith("---") else ({}, text)

    # 按 ## 切，保留每段标题 + 内容
    entries: list[LogEntry] = []
    matches = list(RE_LOG_HEADER.finditer(body))
    for i, m in enumerate(matches):
        title = m.group(1).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        content = body[start:end].strip()

        is_example = title.startswith("[示例]")

        # 从标题解析 kind
        kind = "unknown"
        low = title.lower()
        for k in ("schema-init", "ingest", "feedback", "lint"):
            if k in low:
                kind = k
                break

        # state
        sm = RE_STATE_FIELD.search(content)
        state = sm.group(1).strip().lower() if sm else "unknown"
        if kind == "schema-init" and state == "unknown":
            state = "done"
        if kind == "feedback" and state == "unknown":
            state = "done"  # feedback 的最终落点默认已处理完

        entries.append(
            LogEntry(
                title=title,
                kind=kind,
                state=state,
                body=content,
                is_example=is_example,
            )
        )
    return entries


def _render_log_state_machine() -> None:
    if not LOG_PATH.exists():
        st.warning(f"log.md 不存在 → {LOG_PATH}")
        return

    entries = _parse_log()
    if not entries:
        st.info("log.md 暂无任何条目。")
        return

    show_examples = st.toggle("显示占位示例条目", value=False, help="首次真实 ingest 完成后可关掉以清爽视图")

    real = [e for e in entries if not e.is_example]
    examples = [e for e in entries if e.is_example]

    visible = real + (examples if show_examples else [])

    ingest_entries = [e for e in visible if e.kind == "ingest"]
    other_entries = [e for e in visible if e.kind != "ingest"]

    col_active, col_paused, col_done = st.columns(3)
    buckets = {
        "active": col_active,
        "paused": col_paused,
        "done": col_done,
    }
    headings = {
        "active": "🟢 active",
        "paused": "🟡 paused",
        "done": "⚪ done",
    }
    counts = {s: 0 for s in buckets}
    for e in ingest_entries:
        s = e.state if e.state in buckets else "done"
        counts[s] += 1

    for state_key, col in buckets.items():
        with col:
            st.subheader(f"{headings[state_key]} ({counts[state_key]})")
            bucket_entries = [
                e for e in ingest_entries
                if (e.state if e.state in buckets else "done") == state_key
            ]
            if not bucket_entries:
                st.caption("_（空）_")
            for entry in bucket_entries:
                expanded_default = (state_key == "active") or (state_key == "paused")
                with st.expander(entry.title, expanded=expanded_default):
                    st.markdown(entry.body)

    if other_entries:
        st.divider()
        st.subheader("其他条目（feedback / lint / schema-init）")
        for entry in other_entries:
            icon = {"feedback": "📬", "lint": "🧹", "schema-init": "🧱"}.get(entry.kind, "📝")
            with st.expander(f"{icon} {entry.title}  ·  state={entry.state}"):
                st.markdown(entry.body)


# ---------------------------------------------------------------------------
# Feedback Inbox
# ---------------------------------------------------------------------------

def _render_feedback_inbox() -> None:
    if not INBOX_DIR.exists():
        st.info(f"Inbox 目录尚未创建（V3 引入 Feedback Loop 后自动出现）→ {INBOX_DIR}")
        return

    tickets = sorted(INBOX_DIR.glob("*.md"))
    # 过滤掉 README.md 之类文档
    tickets = [t for t in tickets if t.name.lower() != "readme.md"]

    st.caption(f"{INBOX_DIR}")
    if not tickets:
        st.success("Inbox 清空 ✅ 无待处理 ticket。")
        return

    st.metric("待处理 tickets", len(tickets))
    for t in tickets:
        try:
            content = t.read_text(encoding="utf-8")
        except OSError as exc:
            st.error(f"读取失败 {t.name}: {exc}")
            continue
        with st.expander(t.name):
            st.markdown(content)


# ---------------------------------------------------------------------------
# Tab 布局
# ---------------------------------------------------------------------------

tab_overview, tab_browse, tab_log, tab_feedback = st.tabs(
    ["总览", "页面浏览", "log 状态机", "Feedback Inbox"]
)

with tab_overview:
    _render_overview()

with tab_browse:
    _render_browser()

with tab_log:
    _render_log_state_machine()

with tab_feedback:
    _render_feedback_inbox()

st.divider()
st.caption(
    "本页严格只读：不触发 wiki_write / wiki_index(rebuild=True)。若需重建 index.md / overview.md，"
    "在 Builder 终端手动执行 `python -c \"from src.phy.wiki import wiki_index; print(wiki_index(rebuild=True))\"`。"
)
