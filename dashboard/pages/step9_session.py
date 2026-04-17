"""
Step 9 — 会话持久化

展示内容：
1. 历史会话浏览（实时读取 ~/.harness/sessions/）
2. 会话 JSON 格式预览
3. --resume / /save / /load 的工作原理
4. 实现代码原理
"""
import json
import pathlib
import sys

import streamlit as st

ROOT = pathlib.Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

st.set_page_config(page_title="Step 9 — 会话持久化", page_icon="💾", layout="wide")
st.title("Step 9 · 会话持久化")
st.caption("将对话历史写入磁盘，下次启动时用 --resume 无缝续接")

# ── 学习目标 ──────────────────────────────────────────────────
with st.expander("📋 学习目标", expanded=False):
    st.markdown("""
- 理解如何将 `AgentSession.messages` 序列化为 JSON
- 掌握 `--resume <id>`、`/save`、`/load <id>`、`/sessions` 的用法
- 了解自动保存（REPL 退出时触发）的设计原则
- 查看真实存储在 `~/.harness/sessions/` 的历史会话
""")

tab1, tab2, tab3, tab4 = st.tabs([
    "💾 历史会话",
    "📄 JSON 格式",
    "🔧 命令使用",
    "🔬 代码原理",
])

# ────────────────────────────────────────────────────────────
# Tab 1 — 历史会话浏览
# ────────────────────────────────────────────────────────────
with tab1:
    st.subheader("历史会话列表")

    try:
        from src.session import list_sessions, load_session, sessions_dir
        sessions = list_sessions(limit=20)
        sdir = sessions_dir()
        st.caption(f"存储目录：`{sdir}`")
    except Exception as e:
        st.error(f"无法加载会话模块：{e}")
        sessions = []
        sdir = pathlib.Path.home() / ".harness" / "sessions"

    if not sessions:
        st.info("暂无历史会话。运行 CLI 并输入 /save，或正常退出 REPL（会自动保存）。")
        st.code("python -m src.main\n# 对话几轮后输入 /save 或 Ctrl+C 退出", language="bash")
    else:
        st.success(f"找到 {len(sessions)} 条历史会话")

        col_h1, col_h2, col_h3, col_h4 = st.columns([3, 1, 1, 3])
        col_h1.markdown("**会话 ID**")
        col_h2.markdown("**消息数**")
        col_h3.markdown("**Tokens**")
        col_h4.markdown("**工作目录**")
        st.divider()

        selected_id = None
        for s in sessions:
            c1, c2, c3, c4 = st.columns([3, 1, 1, 3])
            c1.code(s["id"], language=None)
            c2.write(s["msg_count"])
            c3.write(s["total_tokens"])
            c4.write(s["cwd"] or "—")
            if c1.button("查看", key="view_" + s["id"]):
                selected_id = s["id"]

        if selected_id:
            st.divider()
            st.subheader(f"会话详情：{selected_id}")
            try:
                loaded = load_session(selected_id)
                for i, msg in enumerate(loaded.messages):
                    role = msg.get("role", "?")
                    color = {"user": "🧑", "assistant": "🤖", "tool": "🔧"}.get(role, "❓")
                    content = msg.get("content") or str(msg.get("tool_calls", ""))
                    with st.chat_message(role):
                        st.markdown(f"{color} **{role}**")
                        if isinstance(content, str):
                            st.write(content[:500] + ("…" if len(content) > 500 else ""))
                        else:
                            st.json(content)
            except Exception as e:
                st.error(f"加载会话失败：{e}")

# ────────────────────────────────────────────────────────────
# Tab 2 — JSON 格式预览
# ────────────────────────────────────────────────────────────
with tab2:
    st.subheader("会话 JSON 文件格式")
    st.markdown("每个会话存储为一个独立的 `.json` 文件，结构如下：")

    example = {
        "id": "20260417_143022_abcd",
        "created_at": "2026-04-17T14:30:22",
        "cwd": "/Users/foo/my-project",
        "messages": [
            {"role": "user", "content": "帮我重构 utils.py"},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [{
                    "id": "call_001",
                    "type": "function",
                    "function": {"name": "read_file", "arguments": "{\"path\": \"utils.py\"}"},
                }],
            },
            {"role": "tool", "tool_call_id": "call_001", "name": "read_file", "content": "def foo(): ..."},
            {"role": "assistant", "content": "我已经读取了 utils.py，建议将…"},
        ],
        "usage": {
            "prompt_tokens": 1200,
            "completion_tokens": 340,
        },
    }
    st.json(example)

    st.markdown("**字段说明**")
    st.table({
        "字段": ["id", "created_at", "cwd", "messages", "usage"],
        "含义": [
            "时间戳 + 随机后缀，唯一标识",
            "创建时间（ISO 8601）",
            "会话时的工作目录",
            "完整消息历史（OpenAI 格式）",
            "累计 prompt / completion token 用量",
        ],
    })

    st.divider()
    st.subheader("存储路径")
    sdir_display = str(pathlib.Path.home() / ".harness" / "sessions")
    st.code(sdir_display, language="bash")
    st.markdown("""
- 每个会话一个文件，最多保留 **50** 条（旧的自动清理）
- 文件名即会话 ID，方便 `--resume` 直接引用
""")

# ────────────────────────────────────────────────────────────
# Tab 3 — 命令使用
# ────────────────────────────────────────────────────────────
with tab3:
    st.subheader("命令速查")

    st.markdown("**REPL 内置命令**")
    st.table({
        "命令": ["/save", "/sessions", "/load <id>", "/clear"],
        "说明": [
            "将当前对话保存到磁盘，返回 session ID",
            "列出最近 10 条历史会话（ID、消息数、tokens、cwd）",
            "恢复指定会话，替换当前对话历史",
            "清空对话（同时清空工具结果缓存）",
        ],
    })

    st.markdown("**启动参数**")
    st.code("""
# 列出历史会话（不进入 REPL）
python -m src.main --sessions

# 恢复指定会话继续对话
python -m src.main --resume 20260417_143022_abcd

# 组合：恢复会话 + yolo 模式
python -m src.main --resume <id> --yolo
""", language="bash")

    st.markdown("**自动保存规则**")
    col_a, col_b = st.columns(2)
    with col_a:
        st.success("✅ 触发自动保存")
        st.markdown("""
- REPL 中按 **Ctrl+C**（第二次，空闲状态）
- 输入 **EOF**（如 `Ctrl+D`）
- 执行 `/save` 命令
""")
    with col_b:
        st.info("ℹ️ 不触发自动保存")
        st.markdown("""
- 执行 `/exit` 或 `/quit`
- 使用 `--prompt` 单次模式
- 对话历史为空时
""")

    st.divider()
    st.markdown("**典型工作流演示**")
    st.code("""
# 第一天
$ python -m src.main
> 帮我分析 src/agent.py 的结构
Harness  src/agent.py 共 464 行，主要分为...
> /save
  已保存 → 20260417_091500_xyzw
> ^C
  已自动保存会话 → 20260417_091502_abcd
  Bye.

# 第二天，续接昨天的对话
$ python -m src.main --sessions
  20260417_091500_xyzw  4 条消息  1840 tokens  /Users/foo/harness

$ python -m src.main --resume 20260417_091500_xyzw
  已恢复会话（4 条消息）
> 继续，请帮我重构其中的 run_agent 函数
""", language="bash")

# ────────────────────────────────────────────────────────────
# Tab 4 — 代码原理
# ────────────────────────────────────────────────────────────
with tab4:
    st.subheader("核心实现")

    st.markdown("#### `src/session.py` — 序列化 / 反序列化")
    st.code("""
def _session_to_dict(session: AgentSession, session_id: str) -> dict:
    return {
        "id": session_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "cwd": session.cwd,
        "messages": session.messages,   # 直接存 list[dict]，已是 JSON 友好格式
        "usage": {
            "prompt_tokens":     session.usage.prompt_tokens,
            "completion_tokens": session.usage.completion_tokens,
        },
    }

def save_session(session: AgentSession, session_id: str | None = None) -> str:
    sid = session_id or _new_session_id()
    path = _session_path(sid)
    path.write_text(
        json.dumps(_session_to_dict(session, sid), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    _prune_old_sessions()   # 超出 50 条时删除最旧的
    return sid
""", language="python")

    st.markdown("#### `src/cli.py` — /load 替换当前 session")
    st.code("""
# REPL 中使用 session_box（可变容器）代替直接引用
session_box: list[AgentSession] = [session]

# /load 命令实现
new_session = load_session(sid)
session_box[0] = new_session   # 替换当前 session
clear_result_cache()           # 同步清理工具缓存
""", language="python")

    st.markdown("#### 自动保存（Ctrl+C 信号处理）")
    st.code("""
def handle_sigint(sig, frame):
    if agent_running:
        stop_event.set()           # 中断当前任务
        print("正在中断...")
    else:
        cur = session_box[0]
        if cur.messages:
            sid = save_session(cur)
            print(f"已自动保存会话 → {sid}")
        sys.exit(0)
""", language="python")

    st.markdown("#### 会话 ID 设计")
    st.code("""
def _new_session_id() -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")   # 时间有序，方便排序
    suffix = "".join(random.choices(string.ascii_lowercase, k=4))  # 防秒内碰撞
    return ts + "_" + suffix
# 示例：20260417_143022_abcd
""", language="python")

    st.divider()
    st.markdown("""
**设计亮点**

| 问题 | 解决方案 |
|------|---------|
| messages 已是 `list[dict]` | 无需额外序列化，直接 `json.dumps` |
| tool_calls 含嵌套结构 | OpenAI SDK 返回的 dict 本身可序列化 |
| 多会话管理 | 按 `mtime` 排序 + 上限 50 条自动清理 |
| /load 替换 session | `session_box = [session]` 可变容器模式 |
| 秒内 ID 冲突 | 4 位随机小写字母后缀（26^4 = 456976 种） |
""")
