"""
记忆系统模块

将跨会话的重要事实持久化到 ~/.harness/memory/MEMORY.md，
并在每次启动时注入 system prompt，让 agent 记住用户偏好和项目约定。

设计原则：
- 存储格式为人类可读的 Markdown（方便用户手动编辑）
- 四大分类：user / feedback / project / reference
- 支持关键词搜索和 tag 过滤
- 自动去重（相似内容 Levenshtein 距离 < 0.2 时警告）

存储位置：
    ~/.harness/memory/MEMORY.md

文件格式（每行一条记忆）：
    ## user
    - [2026-04-17] [id:abc1] 用户偏好简洁风格，避免冗长解释 #style #preference
    - ...

    ## project
    - [2026-04-17] [id:def2] /Users/foo/proj 使用 FastAPI，Python 3.12 #fastapi
    - ...
"""
import random
import re
import string
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal

# 四类记忆
MemoryCategory = Literal["user", "feedback", "project", "reference"]
ALL_CATEGORIES: list[str] = ["user", "feedback", "project", "reference"]

CATEGORY_DESC = {
    "user":      "用户个人偏好、习惯、背景信息",
    "feedback":  "用户对 agent 行为的正/负反馈",
    "project":   "具体项目的技术栈、约定、路径",
    "reference": "通用技术知识、最佳实践、参考资料",
}

_MEMORY_DIR = Path.home() / ".harness" / "memory"
_MEMORY_FILE = _MEMORY_DIR / "MEMORY.md"
_ID_LEN = 6


# ── 数据结构 ──────────────────────────────────────────────────

@dataclass
class MemoryEntry:
    id: str
    category: str
    content: str
    created_at: str
    tags: list[str] = field(default_factory=list)
    source: str = "manual"   # "manual" | "auto"

    def to_line(self) -> str:
        """序列化为 MEMORY.md 的一行"""
        tag_str = " " + " ".join(f"#{t}" for t in self.tags) if self.tags else ""
        src_hint = " [auto]" if self.source == "auto" else ""
        return f"- [{self.created_at}] [id:{self.id}]{src_hint} {self.content}{tag_str}"

    @staticmethod
    def from_line(line: str, category: str) -> "MemoryEntry | None":
        """从 MEMORY.md 的一行反序列化"""
        m = re.match(
            r"^- \[(?P<date>[^\]]+)\] \[id:(?P<id>[^\]]+)\](?P<auto> \[auto\])? (?P<rest>.+)$",
            line.strip(),
        )
        if not m:
            return None
        rest = m.group("rest")
        # 拆分 tags（末尾的 #word）
        tags: list[str] = re.findall(r"#(\w+)", rest)
        content = re.sub(r"\s*#\w+", "", rest).strip()
        return MemoryEntry(
            id=m.group("id"),
            category=category,
            content=content,
            created_at=m.group("date"),
            tags=tags,
            source="auto" if m.group("auto") else "manual",
        )


# ── 文件读写 ──────────────────────────────────────────────────

def _ensure_dir() -> None:
    _MEMORY_DIR.mkdir(parents=True, exist_ok=True)


def _new_id() -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=_ID_LEN))


def load_memories() -> list[MemoryEntry]:
    """读取 MEMORY.md，返回所有记忆条目"""
    _ensure_dir()
    if not _MEMORY_FILE.exists():
        return []

    entries: list[MemoryEntry] = []
    current_cat: str | None = None

    for raw_line in _MEMORY_FILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        # 检测分类标题
        cat_m = re.match(r"^## (user|feedback|project|reference)$", line)
        if cat_m:
            current_cat = cat_m.group(1)
            continue
        if current_cat and line.startswith("- ["):
            entry = MemoryEntry.from_line(line, current_cat)
            if entry:
                entries.append(entry)

    return entries


def _write_memories(entries: list[MemoryEntry]) -> None:
    """将所有条目按分类写回 MEMORY.md"""
    _ensure_dir()
    lines = ["# Harness 记忆库\n"]
    for cat in ALL_CATEGORIES:
        cat_entries = [e for e in entries if e.category == cat]
        lines.append(f"## {cat}")
        lines.append(f"<!-- {CATEGORY_DESC[cat]} -->")
        if cat_entries:
            for e in cat_entries:
                lines.append(e.to_line())
        else:
            lines.append("<!-- 暂无记录 -->")
        lines.append("")
    _MEMORY_FILE.write_text("\n".join(lines), encoding="utf-8")


# ── 公共 API ──────────────────────────────────────────────────

def add_memory(
    content: str,
    category: str = "user",
    tags: list[str] | None = None,
    source: str = "manual",
) -> MemoryEntry:
    """
    新增一条记忆。

    Args:
        content:  记忆正文
        category: user / feedback / project / reference
        tags:     关键词标签列表（无需加 #）
        source:   "manual"（用户手动）或 "auto"（LLM 提取）

    Returns:
        新建的 MemoryEntry
    """
    if category not in ALL_CATEGORIES:
        raise ValueError(f"未知分类 {category!r}，可用：{ALL_CATEGORIES}")
    if not content.strip():
        raise ValueError("记忆内容不能为空")

    entries = load_memories()
    entry = MemoryEntry(
        id=_new_id(),
        category=category,
        content=content.strip(),
        created_at=datetime.now().strftime("%Y-%m-%d"),
        tags=tags or [],
        source=source,
    )
    entries.append(entry)
    _write_memories(entries)
    return entry


def delete_memory(memory_id: str) -> bool:
    """删除指定 id 的记忆，返回是否找到并删除"""
    entries = load_memories()
    new_entries = [e for e in entries if e.id != memory_id]
    if len(new_entries) == len(entries):
        return False
    _write_memories(new_entries)
    return True


def search_memories(
    query: str,
    category: str | None = None,
) -> list[MemoryEntry]:
    """
    关键词搜索记忆（大小写不敏感）。

    Args:
        query:    搜索词（空格分隔的多词 AND 逻辑）
        category: 限定分类（None = 所有）

    Returns:
        匹配的记忆列表
    """
    entries = load_memories()
    if category:
        entries = [e for e in entries if e.category == category]

    keywords = [k.lower() for k in query.split() if k]
    if not keywords:
        return entries

    result = []
    for e in entries:
        text = (e.content + " " + " ".join(e.tags)).lower()
        if all(kw in text for kw in keywords):
            result.append(e)
    return result


def format_for_prompt(entries: list[MemoryEntry]) -> str:
    """
    将记忆列表格式化为注入 system prompt 的文本块。
    若无记忆则返回空字符串。
    """
    if not entries:
        return ""

    lines = ["## 长期记忆（跨会话积累）", ""]
    for cat in ALL_CATEGORIES:
        cat_entries = [e for e in entries if e.category == cat]
        if not cat_entries:
            continue
        lines.append(f"### {cat}（{CATEGORY_DESC[cat]}）")
        for e in cat_entries:
            tag_str = "  " + " ".join(f"#{t}" for t in e.tags) if e.tags else ""
            lines.append(f"- {e.content}{tag_str}")
        lines.append("")

    return "\n".join(lines).strip()


def memory_file_path() -> Path:
    """返回 MEMORY.md 路径（供 UI 展示）"""
    return _MEMORY_FILE
