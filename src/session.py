"""
会话持久化模块

将 AgentSession 序列化为 JSON 文件，支持：
- 保存当前会话到 ~/.harness/sessions/<id>.json
- 列出所有历史会话（按时间倒序）
- 从文件恢复会话（--resume / /load 命令）

存储结构：
    ~/.harness/
    └── sessions/
        ├── 20260416_143022_abc.json
        ├── 20260416_151800_def.json
        └── ...

JSON 格式：
    {
        "id":        "20260416_143022_abc",
        "created_at": "2026-04-16T14:30:22",
        "cwd":       "/Users/foo/project",
        "messages":  [...],
        "usage":     {"prompt_tokens": 0, "completion_tokens": 0}
    }
"""
import json
import os
import random
import string
from datetime import datetime
from pathlib import Path

from src.agent import AgentSession, TokenUsage

# 会话目录（遵循 Unix 惯例放在 HOME 下）
_SESSIONS_DIR = Path.home() / ".harness" / "sessions"
_MAX_SESSIONS = 50          # 超出时自动删除最旧的会话
_SESSION_ID_SUFFIX_LEN = 4  # 随机后缀长度，防止同一秒内碰撞


# ── 会话目录初始化 ────────────────────────────────────────────

def _ensure_dir() -> Path:
    _SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    return _SESSIONS_DIR


# ── ID 与路径 ─────────────────────────────────────────────────

def _new_session_id() -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = "".join(random.choices(string.ascii_lowercase, k=_SESSION_ID_SUFFIX_LEN))
    return ts + "_" + suffix


def _session_path(session_id: str) -> Path:
    return _SESSIONS_DIR / (session_id + ".json")


# ── 序列化 / 反序列化 ─────────────────────────────────────────

def _session_to_dict(session: AgentSession, session_id: str) -> dict:
    return {
        "id": session_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "cwd": session.cwd,
        "messages": session.messages,
        "usage": {
            "prompt_tokens": session.usage.prompt_tokens,
            "completion_tokens": session.usage.completion_tokens,
        },
    }


def _dict_to_session(data: dict) -> AgentSession:
    usage = TokenUsage(
        prompt_tokens=data.get("usage", {}).get("prompt_tokens", 0),
        completion_tokens=data.get("usage", {}).get("completion_tokens", 0),
    )
    return AgentSession(
        messages=data.get("messages", []),
        usage=usage,
        cwd=data.get("cwd", os.getcwd()),
    )


# ── 公共 API ──────────────────────────────────────────────────

def save_session(session: AgentSession, session_id: str | None = None) -> str:
    """
    将会话保存到磁盘。

    Args:
        session:    要保存的会话对象
        session_id: 指定 ID（用于覆盖更新）；None 时自动生成新 ID

    Returns:
        使用的 session_id
    """
    if not session.messages:
        raise ValueError("会话为空，无需保存")

    _ensure_dir()
    sid = session_id or _new_session_id()
    path = _session_path(sid)
    path.write_text(
        json.dumps(_session_to_dict(session, sid), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    _prune_old_sessions()
    return sid


def load_session(session_id: str) -> AgentSession:
    """
    从磁盘加载指定 ID 的会话。

    Raises:
        FileNotFoundError: session_id 不存在
        ValueError:        文件格式损坏
    """
    path = _session_path(session_id)
    if not path.exists():
        raise FileNotFoundError("未找到会话：" + session_id)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError("会话文件损坏：" + str(e)) from e
    return _dict_to_session(data)


def list_sessions(limit: int = 20) -> list[dict]:
    """
    列出最近的会话（按修改时间倒序）。

    Returns:
        list of {id, created_at, cwd, msg_count, total_tokens}
    """
    _ensure_dir()
    files = sorted(
        _SESSIONS_DIR.glob("*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:limit]

    result = []
    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            result.append({
                "id":           data.get("id", f.stem),
                "created_at":   data.get("created_at", ""),
                "cwd":          data.get("cwd", ""),
                "msg_count":    len(data.get("messages", [])),
                "total_tokens": (
                    data.get("usage", {}).get("prompt_tokens", 0)
                    + data.get("usage", {}).get("completion_tokens", 0)
                ),
            })
        except Exception:
            continue
    return result


def delete_session(session_id: str) -> bool:
    """删除指定会话，返回是否成功"""
    path = _session_path(session_id)
    if path.exists():
        path.unlink()
        return True
    return False


def _prune_old_sessions() -> None:
    """超出 _MAX_SESSIONS 时删除最旧的会话"""
    files = sorted(
        _SESSIONS_DIR.glob("*.json"),
        key=lambda p: p.stat().st_mtime,
    )
    for f in files[: max(0, len(files) - _MAX_SESSIONS)]:
        f.unlink(missing_ok=True)


def sessions_dir() -> Path:
    """返回会话存储目录（供 UI 展示）"""
    return _SESSIONS_DIR
