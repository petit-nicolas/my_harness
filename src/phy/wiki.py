"""Physics Wiki 四工具（src/phy/wiki.py）— V1.5 落地。

提供 wiki_read / wiki_search / wiki_write / wiki_index 四个 Harness 工具：

    | 工具         | builder | runner | 用途                                  |
    |--------------|:-------:|:------:|---------------------------------------|
    | wiki_read    |    ✅   |   ✅   | 按 page_id 读 wiki 页（含 frontmatter）|
    | wiki_search  |    ✅   |   ✅   | 多维检索（all/title/body/wikilink/subject）|
    | wiki_write   |    ✅   |   ❌   | 创建/覆盖 wiki 页（最小 schema 校验）|
    | wiki_index   |    ✅   |   ❌   | 扫全树统计 + 可选重建 index.md/overview.md |

V1.5 设计原则：
- 零外部依赖（手写最小 frontmatter 解析器，不引入 PyYAML）
- wiki_write 仅做"最小校验 + 告警"，严格 lint 留给 V2.5 的 `wiki_lint`
- mode 分级通过 `get_tools(mode)` / `get_executors(mode)` 在注册时硬过滤，
  runner mode 下 wiki_write/wiki_index **根本不出现在工具表**

V3 通过 `src/prompt.py --mode physics` 把这些工具合并到主 `TOOLS` 注册表。
"""
from __future__ import annotations

import datetime as _dt
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Optional


# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

WIKI_ROOT = Path("res/phy/wiki")
META_PAGE_IDS = {"index", "log", "overview"}
META_SUBDIRS = {"sources", "feedback"}
ALLOWED_LEVELS = {"basic", "advanced", "competition", "meta"}
ALLOWED_SUBJECTS = {"mechanics", "electromagnetism", "thermodynamics", "optics", "modern", "meta"}
ID_RE = re.compile(r"^[a-z0-9][a-z0-9\-]*(/[a-z0-9][a-z0-9\-]*)*$")
WIKILINK_RE = re.compile(r"\[\[([^\]|#]+?)(?:\|[^\]]+?)?(?:#[^\]]+?)?\]\]")
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)
SEARCH_MAX_RESULTS = 30
SEARCH_SNIPPET_CHARS = 80


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

@dataclass
class WikiPage:
    """已解析的 wiki 页：frontmatter（dict）+ body（去掉 frontmatter 的 markdown）。"""

    page_id: str
    path: Path
    frontmatter: dict[str, Any]
    body: str
    raw: str

    @property
    def title(self) -> str:
        return str(self.frontmatter.get("title", self.page_id))

    @property
    def level(self) -> str:
        return str(self.frontmatter.get("level", ""))

    @property
    def subject(self) -> str:
        return str(self.frontmatter.get("subject", self._infer_subject()))

    def _infer_subject(self) -> str:
        if "/" in self.page_id:
            head = self.page_id.split("/", 1)[0]
            if head in ALLOWED_SUBJECTS or head in META_SUBDIRS:
                return head
        return "meta" if self.page_id in META_PAGE_IDS else ""

    def wikilinks(self) -> list[str]:
        return WIKILINK_RE.findall(self.body)


# ---------------------------------------------------------------------------
# 极简 frontmatter 解析（不引入 PyYAML）
# ---------------------------------------------------------------------------

def _parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """解析 markdown 顶部的 YAML-ish frontmatter。

    支持：标量（str/int/float/bool/date）、行内列表 [a, b]、多行块列表（- item）。
    不支持：嵌套字典、锚点别名等高级 YAML。
    返回 (frontmatter_dict, body_text)；无 frontmatter 时返回 ({}, text)。
    """
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text

    fm_text, body = m.group(1), m.group(2)
    data: dict[str, Any] = {}
    current_key: Optional[str] = None
    current_list: Optional[list[Any]] = None

    for raw_line in fm_text.splitlines():
        line = raw_line.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue

        # 多行列表项：前导 "- "
        stripped = line.lstrip()
        if stripped.startswith("- ") and current_list is not None:
            current_list.append(_coerce_scalar(stripped[2:].strip()))
            continue

        # key: value 形式
        if ":" in line and not line.startswith(" "):
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip()
            current_key = key
            current_list = None
            if not val:
                # 留待下一行的列表项填充
                data[key] = []
                current_list = data[key]
            elif val.startswith("[") and val.endswith("]"):
                inner = val[1:-1].strip()
                if not inner:
                    data[key] = []
                else:
                    items = [_coerce_scalar(x.strip()) for x in inner.split(",")]
                    data[key] = items
            else:
                data[key] = _coerce_scalar(val)

    return data, body


def _coerce_scalar(raw: str) -> Any:
    """把字符串值还原为合适的 Python 类型。"""
    s = raw.strip()
    if not s:
        return ""
    # 引号包裹 → 去引号
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        return s[1:-1]
    low = s.lower()
    if low in ("true", "yes"):
        return True
    if low in ("false", "no"):
        return False
    if low in ("null", "none", "~"):
        return None
    # 日期 YYYY-MM-DD
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        try:
            return _dt.date.fromisoformat(s)
        except ValueError:
            return s
    # int / float
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        pass
    return s


def _serialize_frontmatter(fm: dict[str, Any]) -> str:
    """把 dict 序列化回 YAML-ish frontmatter，保留稳定顺序。"""
    lines = ["---"]
    preferred = [
        "id", "title", "level", "subject",
        "prerequisites", "tags", "sources",
        "source", "original_path", "covers",
        "ingest_log_ref",
        "created", "updated",
    ]
    seen: set[str] = set()
    keys = [k for k in preferred if k in fm] + [k for k in fm if k not in preferred]
    for key in keys:
        if key in seen:
            continue
        seen.add(key)
        val = fm[key]
        lines.append(_serialize_kv(key, val))
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def _serialize_kv(key: str, val: Any) -> str:
    if isinstance(val, list):
        if not val:
            return f"{key}: []"
        if all(_is_inline_scalar(v) for v in val):
            return f"{key}: [{', '.join(_serialize_inline(v) for v in val)}]"
        body = "\n".join(f"  - {_serialize_inline(v)}" for v in val)
        return f"{key}:\n{body}"
    return f"{key}: {_serialize_inline(val)}"


def _is_inline_scalar(v: Any) -> bool:
    return isinstance(v, (str, int, float, bool, _dt.date)) or v is None


def _serialize_inline(v: Any) -> str:
    if isinstance(v, _dt.date):
        return v.isoformat()
    if isinstance(v, bool):
        return "true" if v else "false"
    if v is None:
        return "null"
    return str(v)


# ---------------------------------------------------------------------------
# page_id ↔ 文件路径映射
# ---------------------------------------------------------------------------

def _id_to_path(page_id: str) -> Path:
    page_id = page_id.strip().lstrip("/").rstrip("/")
    return WIKI_ROOT / f"{page_id}.md"


def _path_to_id(path: Path) -> str:
    return str(path.relative_to(WIKI_ROOT).with_suffix("")).replace("\\", "/")


def _is_valid_id(page_id: str) -> bool:
    if not page_id:
        return False
    if page_id in META_PAGE_IDS:
        return True
    return bool(ID_RE.match(page_id))


def _iter_wiki_files(*, include_meta: bool = True, include_sources: bool = True) -> Iterable[Path]:
    if not WIKI_ROOT.exists():
        return
    for path in sorted(WIKI_ROOT.rglob("*.md")):
        rel = path.relative_to(WIKI_ROOT)
        # 跳过 README
        if rel.name.upper() == "README.MD":
            continue
        page_id = _path_to_id(path)
        if not include_meta and page_id in META_PAGE_IDS:
            continue
        if not include_sources and rel.parts and rel.parts[0] == "sources":
            continue
        # feedback/ 永远跳过（属于反馈队列，不是 wiki 本体）
        if rel.parts and rel.parts[0] == "feedback":
            continue
        yield path


def _load_page(page_id: str) -> Optional[WikiPage]:
    path = _id_to_path(page_id)
    if not path.exists() or not path.is_file():
        return None
    raw = path.read_text(encoding="utf-8")
    fm, body = _parse_frontmatter(raw)
    return WikiPage(page_id=page_id, path=path, frontmatter=fm, body=body, raw=raw)


# ---------------------------------------------------------------------------
# 工具 1：wiki_read
# ---------------------------------------------------------------------------

def wiki_read(page_id: str) -> str:
    if not _is_valid_id(page_id):
        return f"错误：page_id 格式非法 → {page_id!r}（要求 kebab-case，例如 mechanics/newton-second-law）"
    page = _load_page(page_id)
    if page is None:
        suggestions = _suggest_similar_ids(page_id, limit=5)
        hint = ("\n建议（最相似的现有页面）：\n  - " + "\n  - ".join(suggestions)) if suggestions else ""
        return f"错误：wiki 页不存在 → {page_id}（路径 {_id_to_path(page_id)}）{hint}"
    return page.raw


def _suggest_similar_ids(page_id: str, *, limit: int = 5) -> list[str]:
    """简易"建议清单"：先按子串包含，再按公共前缀长度排序。"""
    target = page_id.lower()
    candidates = []
    for path in _iter_wiki_files():
        cand_id = _path_to_id(path)
        score = 0
        if target in cand_id.lower():
            score += 100
        common = _common_prefix_len(target, cand_id.lower())
        score += common
        if score > 0:
            candidates.append((score, cand_id))
    candidates.sort(key=lambda x: (-x[0], x[1]))
    return [cid for _, cid in candidates[:limit]]


def _common_prefix_len(a: str, b: str) -> int:
    n = min(len(a), len(b))
    for i in range(n):
        if a[i] != b[i]:
            return i
    return n


# ---------------------------------------------------------------------------
# 工具 2：wiki_search
# ---------------------------------------------------------------------------

ALLOWED_SCOPES = {"all", "title", "body", "wikilink", "subject"}


def wiki_search(
    query: str,
    *,
    scope: str = "all",
    limit: int = 20,
    case_sensitive: bool = False,
) -> str:
    if not query.strip():
        return "错误：query 不能为空"
    if scope not in ALLOWED_SCOPES:
        return f"错误：scope 必须是 {sorted(ALLOWED_SCOPES)}，当前 {scope!r}"
    if limit < 1:
        limit = 1
    limit = min(limit, SEARCH_MAX_RESULTS)

    needle = query if case_sensitive else query.lower()
    results: list[tuple[str, str, str]] = []  # (page_id, title, snippet)

    for path in _iter_wiki_files():
        page_id = _path_to_id(path)
        page = _load_page(page_id)
        if page is None:
            continue

        haystack: Optional[str] = None
        snippet: Optional[str] = None

        if scope == "title":
            t = page.title
            if (t if case_sensitive else t.lower()).find(needle) >= 0:
                snippet = t
        elif scope == "body":
            haystack = page.body
        elif scope == "wikilink":
            for link in page.wikilinks():
                if (link if case_sensitive else link.lower()).find(needle) >= 0:
                    snippet = f"→ [[{link}]]"
                    break
        elif scope == "subject":
            subj = page.subject
            if (subj if case_sensitive else subj.lower()) == needle:
                snippet = f"subject={subj}"
        else:  # "all"
            haystack = page.raw
            t = page.title
            if (t if case_sensitive else t.lower()).find(needle) >= 0:
                snippet = f"[title hit] {t}"

        if snippet is None and haystack is not None:
            hay = haystack if case_sensitive else haystack.lower()
            idx = hay.find(needle)
            if idx >= 0:
                start = max(0, idx - SEARCH_SNIPPET_CHARS // 2)
                end = min(len(haystack), idx + len(needle) + SEARCH_SNIPPET_CHARS // 2)
                snippet = haystack[start:end].replace("\n", " ⏎ ")
                if start > 0:
                    snippet = "..." + snippet
                if end < len(haystack):
                    snippet = snippet + "..."

        if snippet is not None:
            results.append((page_id, page.title, snippet))
            if len(results) >= limit:
                break

    if not results:
        return f"（无匹配）query={query!r} scope={scope}"

    lines = [f"找到 {len(results)} 条匹配（scope={scope}, query={query!r}）：", ""]
    for page_id, title, snippet in results:
        lines.append(f"## {page_id}")
        lines.append(f"- **title**: {title}")
        lines.append(f"- **snippet**: {snippet}")
        lines.append("")
    return "\n".join(lines).rstrip()


# ---------------------------------------------------------------------------
# 工具 3：wiki_write（builder only）
# ---------------------------------------------------------------------------

@dataclass
class WriteReport:
    page_id: str
    path: Path
    bytes_written: int
    created: bool
    warnings: list[str] = field(default_factory=list)
    auto_fixes: list[str] = field(default_factory=list)

    def render(self) -> str:
        verb = "创建" if self.created else "覆盖"
        head = f"已{verb} {self.page_id} → {self.path}（{self.bytes_written} 字节）"
        lines = [head]
        for fix in self.auto_fixes:
            lines.append(f"  [auto-fix] {fix}")
        for warn in self.warnings:
            lines.append(f"  [WARN] {warn}")
        return "\n".join(lines)


def wiki_write(page_id: str, content: str, *, today: Optional[_dt.date] = None) -> str:
    if not _is_valid_id(page_id):
        return (
            f"错误：page_id 格式非法 → {page_id!r}\n"
            "约定：kebab-case，subject/slug，例如 mechanics/newton-second-law；"
            "meta 单例只允许 index/log/overview。"
        )

    today = today or _dt.date.today()
    fm, body = _parse_frontmatter(content)
    warnings: list[str] = []
    auto_fixes: list[str] = []

    has_frontmatter = bool(fm) or content.lstrip().startswith("---")
    if not has_frontmatter:
        return (
            f"错误：内容缺少 YAML frontmatter（必须以 --- 开头）。\n"
            f"参考 res/phy/schemas/PHYSICS_SCHEMA.md §1 字段约定。"
        )

    fm.setdefault("id", page_id)
    if fm.get("id") != page_id:
        warnings.append(f"frontmatter.id={fm.get('id')!r} 与 page_id={page_id!r} 不一致")

    if "title" not in fm:
        return "错误：frontmatter 缺必填字段 title"
    if "level" not in fm:
        return "错误：frontmatter 缺必填字段 level"
    if fm["level"] not in ALLOWED_LEVELS:
        warnings.append(f"level={fm['level']!r} 不在 {sorted(ALLOWED_LEVELS)}，请确认是否笔误")

    inferred_subject = page_id.split("/", 1)[0] if "/" in page_id else "meta"
    if page_id not in META_PAGE_IDS and "subject" not in fm:
        fm["subject"] = inferred_subject
        auto_fixes.append(f"subject 未填，按 page_id 推断为 {inferred_subject!r}")
    elif "subject" in fm and inferred_subject not in (fm["subject"], "meta"):
        if page_id not in META_PAGE_IDS:
            warnings.append(
                f"subject={fm['subject']!r} 与路径前缀 {inferred_subject!r} 不一致"
            )

    if "created" not in fm:
        fm["created"] = today
        auto_fixes.append(f"created 未填，自动注入 {today.isoformat()}")
    fm["updated"] = today
    auto_fixes.append(f"updated 自动刷新为 {today.isoformat()}")

    final = _serialize_frontmatter(fm) + "\n" + body.lstrip("\n")

    path = _id_to_path(page_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    created = not path.exists()
    path.write_text(final, encoding="utf-8")

    report = WriteReport(
        page_id=page_id,
        path=path,
        bytes_written=len(final.encode("utf-8")),
        created=created,
        warnings=warnings,
        auto_fixes=auto_fixes,
    )
    return report.render()


# ---------------------------------------------------------------------------
# 工具 4：wiki_index（builder only）
# ---------------------------------------------------------------------------

INDEX_AUTOGEN_BEGIN = "<!-- BEGIN wiki_index AUTOGEN: do not edit by hand -->"
INDEX_AUTOGEN_END = "<!-- END wiki_index AUTOGEN -->"


def wiki_index(*, rebuild: bool = False) -> str:
    if not WIKI_ROOT.exists():
        return f"错误：wiki 根目录不存在 → {WIKI_ROOT}"

    pages_by_subject: dict[str, list[WikiPage]] = defaultdict(list)
    pages_by_level: dict[str, list[WikiPage]] = defaultdict(list)
    backlinks: dict[str, list[str]] = defaultdict(list)
    broken_links: list[tuple[str, str]] = []
    all_pages: list[WikiPage] = []

    for path in _iter_wiki_files(include_meta=False, include_sources=False):
        page_id = _path_to_id(path)
        page = _load_page(page_id)
        if page is None:
            continue
        all_pages.append(page)
        pages_by_subject[page.subject or "(unknown)"].append(page)
        pages_by_level[page.level or "(unknown)"].append(page)

    sources_pages: list[WikiPage] = []
    for path in _iter_wiki_files(include_meta=False, include_sources=True):
        page_id = _path_to_id(path)
        if not page_id.startswith("sources/"):
            continue
        page = _load_page(page_id)
        if page is not None:
            sources_pages.append(page)

    all_ids = {p.page_id for p in all_pages} | {p.page_id for p in sources_pages}
    for page in all_pages + sources_pages:
        for link in page.wikilinks():
            if link in all_ids:
                backlinks[link].append(page.page_id)
            else:
                broken_links.append((page.page_id, link))

    summary_lines = [
        "# wiki_index 扫描摘要",
        "",
        f"- 概念页总数: {len(all_pages)}",
        f"- 资料摘要页总数: {len(sources_pages)}",
        f"- 反向链接总数: {sum(len(v) for v in backlinks.values())}",
        f"- 断裂链接数: {len(broken_links)}",
        "",
        "## 学科分布",
    ]
    if pages_by_subject:
        for subj in sorted(pages_by_subject):
            summary_lines.append(f"- {subj}: {len(pages_by_subject[subj])} 页")
    else:
        summary_lines.append("- （空）")

    summary_lines += ["", "## Level 分布"]
    if pages_by_level:
        for lv in sorted(pages_by_level):
            summary_lines.append(f"- {lv}: {len(pages_by_level[lv])} 页")
    else:
        summary_lines.append("- （空）")

    if broken_links:
        summary_lines += ["", "## 断裂链接（前 20 条）"]
        for src, target in broken_links[:20]:
            summary_lines.append(f"- {src} → [[{target}]] （目标不存在）")

    if not rebuild:
        summary_lines += ["", "_提示：rebuild=true 才会真的写回 index.md / overview.md_"]
        return "\n".join(summary_lines)

    _rewrite_index_md(pages_by_subject, sources_pages, backlinks)
    _rewrite_overview_md(pages_by_subject, pages_by_level, sources_pages, broken_links)
    summary_lines += ["", "**已重写**: index.md / overview.md（仅 AUTOGEN 段）"]
    return "\n".join(summary_lines)


def _autogen_block(content_lines: list[str]) -> str:
    return "\n".join([INDEX_AUTOGEN_BEGIN, *content_lines, INDEX_AUTOGEN_END])


def _splice_autogen(text: str, new_block: str, *, anchor: str) -> str:
    """把 AUTOGEN 段嵌入到指定 anchor 之后；已存在则替换。"""
    pattern = re.compile(
        re.escape(INDEX_AUTOGEN_BEGIN) + ".*?" + re.escape(INDEX_AUTOGEN_END),
        re.DOTALL,
    )
    if pattern.search(text):
        return pattern.sub(new_block, text)
    if anchor in text:
        return text.replace(anchor, anchor + "\n\n" + new_block, 1)
    return text.rstrip() + "\n\n" + new_block + "\n"


def _rewrite_index_md(
    by_subject: dict[str, list[WikiPage]],
    sources_pages: list[WikiPage],
    backlinks: dict[str, list[str]],
) -> None:
    path = WIKI_ROOT / "index.md"
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")

    lines: list[str] = ["", "## 自动生成 — 学科索引", ""]
    if by_subject:
        for subj in sorted(by_subject):
            lines.append(f"### {subj}")
            for page in sorted(by_subject[subj], key=lambda p: p.page_id):
                lines.append(f"- [[{page.page_id}]] — {page.title}")
            lines.append("")
    else:
        lines.append("_（暂无概念页）_")
        lines.append("")

    if sources_pages:
        lines += ["## 自动生成 — 资料摘要页", ""]
        for page in sorted(sources_pages, key=lambda p: p.page_id):
            lines.append(f"- [[{page.page_id}]] — {page.title}")
        lines.append("")

    if backlinks:
        lines += ["## 自动生成 — 反向链接", ""]
        for target in sorted(backlinks):
            refs = backlinks[target]
            lines.append(f"- **{target}** ← 被引用 {len(refs)} 次")
            for ref in sorted(set(refs)):
                lines.append(f"    - {ref}")
        lines.append("")

    block = _autogen_block(lines)
    new_text = _splice_autogen(text, block, anchor="## 反向链接索引")
    path.write_text(new_text, encoding="utf-8")


def _rewrite_overview_md(
    by_subject: dict[str, list[WikiPage]],
    by_level: dict[str, list[WikiPage]],
    sources_pages: list[WikiPage],
    broken_links: list[tuple[str, str]],
) -> None:
    path = WIKI_ROOT / "overview.md"
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")

    lines = ["", "## 自动生成 — 当前实际统计", ""]
    total_pages = sum(len(v) for v in by_subject.values())
    lines.append(f"- 概念页总数: **{total_pages}**")
    lines.append(f"- 资料摘要页总数: **{len(sources_pages)}**")
    lines.append(f"- 已 ingest 教材章节（按 sources/ 估算）: **{len(sources_pages)}**")
    lines.append(f"- 断裂链接: **{len(broken_links)}**")
    lines.append("")
    lines.append("### 学科分布（实际）")
    if by_subject:
        for subj in sorted(by_subject):
            lines.append(f"- {subj}: {len(by_subject[subj])} 页")
    else:
        lines.append("_（暂无）_")
    lines.append("")
    lines.append("### Level 分布（实际）")
    if by_level:
        for lv in sorted(by_level):
            lines.append(f"- {lv}: {len(by_level[lv])} 页")
    else:
        lines.append("_（暂无）_")
    lines.append("")

    block = _autogen_block(lines)
    new_text = _splice_autogen(text, block, anchor="## 知识库统计")
    path.write_text(new_text, encoding="utf-8")


# ---------------------------------------------------------------------------
# Harness 工具注册（OpenAI function-calling 格式 + mode 分级）
# ---------------------------------------------------------------------------

WIKI_TOOLS_RUNNER: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "wiki_read",
            "description": (
                "读取一个 wiki 页面的完整 markdown 内容（含 frontmatter）。"
                "page_id 形如 'mechanics/newton-second-law'；"
                "meta 单例只允许 'index' / 'log' / 'overview'。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "page_id": {
                        "type": "string",
                        "description": "wiki 页 id，与文件路径对齐（不含 .md 后缀）",
                    },
                },
                "required": ["page_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "wiki_search",
            "description": (
                "在 physics wiki 中检索内容。"
                "scope=all 全文搜；title 仅标题；body 仅正文；"
                "wikilink 找引用了某 id 的页面（反向链接搜索）；"
                "subject 按学科精确过滤（mechanics/electromagnetism 等）。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "检索关键词"},
                    "scope": {
                        "type": "string",
                        "enum": sorted(ALLOWED_SCOPES),
                        "default": "all",
                    },
                    "limit": {"type": "integer", "default": 20, "description": f"最多返回结果数（≤{SEARCH_MAX_RESULTS}）"},
                    "case_sensitive": {"type": "boolean", "default": False},
                },
                "required": ["query"],
            },
        },
    },
]

WIKI_TOOLS_BUILDER_ONLY: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "wiki_write",
            "description": (
                "创建或覆盖一个 wiki 页。content 必须是完整的 markdown，"
                "顶部包含 YAML frontmatter（最少 title + level）。"
                "工具会自动注入 created/updated 字段，并对 id/subject 与路径不一致给出告警。"
                "**严格 schema lint 由 V2.5 wiki_lint 工具承担。**"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "page_id": {"type": "string", "description": "wiki 页 id（与路径对齐）"},
                    "content": {
                        "type": "string",
                        "description": "完整 markdown，包含 frontmatter 与正文",
                    },
                },
                "required": ["page_id", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "wiki_index",
            "description": (
                "扫描 wiki 全树，统计学科/level 分布、反向链接、断裂链接。"
                "rebuild=false 时仅返回报告；rebuild=true 时把 AUTOGEN 段写回 "
                "index.md 与 overview.md（手写区域不动）。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "rebuild": {
                        "type": "boolean",
                        "default": False,
                        "description": "true 时真正改写 index.md / overview.md 的 AUTOGEN 段",
                    },
                },
                "required": [],
            },
        },
    },
]


def get_tools(mode: str) -> list[dict]:
    """按 mode 返回该角色可见的 wiki 工具列表（schema 部分）。"""
    if mode == "builder":
        return WIKI_TOOLS_RUNNER + WIKI_TOOLS_BUILDER_ONLY
    if mode == "runner":
        return WIKI_TOOLS_RUNNER
    raise ValueError(f"mode 必须是 'builder' 或 'runner'，当前 {mode!r}")


def get_executors(mode: str) -> dict[str, Any]:
    """按 mode 返回 name → executor 函数 的映射，用于合并到主 _TOOL_EXECUTORS。"""
    runner = {
        "wiki_read":   lambda args: wiki_read(args["page_id"]),
        "wiki_search": lambda args: wiki_search(
            args["query"],
            scope=args.get("scope", "all"),
            limit=args.get("limit", 20),
            case_sensitive=args.get("case_sensitive", False),
        ),
    }
    if mode == "runner":
        return runner
    if mode == "builder":
        return {
            **runner,
            "wiki_write":  lambda args: wiki_write(args["page_id"], args["content"]),
            "wiki_index":  lambda args: wiki_index(rebuild=args.get("rebuild", False)),
        }
    raise ValueError(f"mode 必须是 'builder' 或 'runner'，当前 {mode!r}")
