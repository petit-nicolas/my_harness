"""
Step 11 — 高级安全防护 + Hooks 扩展机制

展示内容：
1. Hooks 机制：pre/post_tool_use 实时演示
2. settings.json 规则化策略（白名单/黑名单/可信路径）
3. 三层安全架构总览
4. 审计日志浏览
"""
import json
import pathlib
import sys

import streamlit as st

ROOT = pathlib.Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

st.set_page_config(page_title="Step 11 — Hooks 扩展", page_icon="🔩", layout="wide")
st.title("Step 11 · 高级安全防护 + Hooks 扩展机制")
st.caption("可配置的策略规则 + 工具执行前后的钩子系统，让 agent 更安全、更可扩展")

with st.expander("📋 学习目标", expanded=False):
    st.markdown("""
- 理解 Hooks（钩子）机制：pre_tool_use / post_tool_use 的触发时机
- 掌握 settings.json 中的 allow/block 规则和优先级
- 了解三层安全架构：Hook 拦截 → Policy 策略 → permissions 内置规则
- 查看 audit.log 中的工具调用审计记录
""")

tab1, tab2, tab3, tab4 = st.tabs([
    "🔩 Hooks 机制",
    "⚙️ settings.json",
    "🛡️ 三层安全架构",
    "📋 审计日志",
])

# ────────────────────────────────────────────────────────────
# Tab 1 — Hooks 演示
# ────────────────────────────────────────────────────────────
with tab1:
    st.subheader("Hooks 机制")

    col1, col2 = st.columns([1, 1])
    with col1:
        st.markdown("#### 工作流程")
        st.markdown("""
```
用户输入
  ↓
Agent 决定调用工具
  ↓
① pre_tool_use hooks 运行
    → 返回 False → 跳过工具（拦截）
    → 返回 True / None → 继续
  ↓
② Policy 层（settings.json）
  ↓
③ permissions 层（硬编码规则）
  ↓
工具实际执行
  ↓
④ post_tool_use hooks 运行
    → 可修改返回结果
  ↓
结果返回模型
```
""")

    with col2:
        st.markdown("#### 内置默认 Hooks")
        st.table({
            "Hook": ["_audit_log_pre", "_stats_counter_pre", "_audit_log_post"],
            "阶段": ["pre", "pre", "post"],
            "功能": [
                "记录工具名+参数摘要到 audit.log",
                "统计本次会话各工具调用次数",
                "记录工具结果摘要到 audit.log",
            ],
        })

    st.divider()

    st.markdown("#### 实时 Hooks 模拟")
    st.markdown("输入一次工具调用，查看 pre/post hook 的执行过程：")

    sim_tool = st.selectbox("工具名", ["run_shell", "read_file", "write_file", "grep_search", "list_files"])
    if sim_tool == "run_shell":
        sim_args_str = st.text_input("参数（JSON）", '{"command": "git status"}')
        sim_result = st.text_input("模拟执行结果", "On branch main\nnothing to commit")
    elif sim_tool == "read_file":
        sim_args_str = st.text_input("参数（JSON）", '{"path": "src/agent.py"}')
        sim_result = st.text_input("模拟执行结果", "def run_agent(...):\n    ...")
    else:
        sim_args_str = st.text_input("参数（JSON）", '{"path": "."}')
        sim_result = st.text_input("模拟执行结果", "src/\n  agent.py\n  tools.py")

    if st.button("▶ 模拟执行", use_container_width=True):
        try:
            sim_args = json.loads(sim_args_str)
        except Exception:
            st.error("参数格式错误，需为合法 JSON")
            st.stop()

        try:
            from src.hooks import HookRegistry, HookEvent, _audit_log_pre, _stats_counter_pre, _audit_log_post

            reg = HookRegistry()
            log_lines = []

            def demo_pre(event: HookEvent):
                log_lines.append(f"[pre] `{event.tool_name}` args={json.dumps(event.arguments, ensure_ascii=False)[:80]}")
                return True

            def demo_post(event: HookEvent):
                log_lines.append(f"[post] `{event.tool_name}` result_len={len(event.result or '')} preview={repr((event.result or '')[:60])}")
                return None

            reg.register_pre(demo_pre)
            reg.register_post(demo_post)

            allowed, reason = reg.run_pre(sim_tool, sim_args)
            final_result = reg.run_post(sim_tool, sim_args, sim_result)

            st.success("✅ 执行流程完成" if allowed else f"🚫 被 Hook 拦截：{reason}")
            for line in log_lines:
                st.markdown(f"- {line}")
            st.markdown(f"**最终结果：** `{final_result[:120]}`")
        except Exception as e:
            st.error(f"模拟失败：{e}")

    st.divider()
    st.markdown("#### 自定义 Hook 示例")
    st.code("""
from src.hooks import HOOKS, HookEvent

# 示例1：拦截所有 sudo 命令
@HOOKS.pre_tool_use
def block_sudo(event: HookEvent) -> bool | None:
    if event.tool_name == "run_shell":
        cmd = event.arguments.get("command", "")
        if cmd.startswith("sudo"):
            return False   # 返回 False → 阻止执行
    return True   # 其他命令放行

# 示例2：在结果前追加时间戳
@HOOKS.post_tool_use
def add_timestamp(event: HookEvent) -> str | None:
    from datetime import datetime
    ts = datetime.now().strftime("%H:%M:%S")
    return f"[{ts}] " + (event.result or "")
""", language="python")

# ────────────────────────────────────────────────────────────
# Tab 2 — settings.json 规则编辑器
# ────────────────────────────────────────────────────────────
with tab2:
    st.subheader("settings.json 规则配置")

    try:
        from src.security import (
            load_settings, save_settings, settings_path,
            assess_shell_policy, assess_file_policy, PolicyDecision,
        )
        sec_available = True
    except Exception as e:
        st.error(f"安全模块加载失败：{e}")
        sec_available = False

    if sec_available:
        spath = settings_path()
        st.caption(f"配置文件：`{spath}`")

        settings = load_settings()

        col_l, col_r = st.columns([1, 1])

        with col_l:
            st.markdown("**Shell 白名单（allow）**")
            allow_list = st.text_area(
                "每行一条 glob 规则",
                value="\n".join(settings.get("shell", {}).get("allow", [])),
                height=180,
                key="allow_list",
            )
            st.markdown("**Shell 黑名单（block）**")
            block_list = st.text_area(
                "每行一条 glob 规则",
                value="\n".join(settings.get("shell", {}).get("block", [])),
                height=120,
                key="block_list",
            )

        with col_r:
            st.markdown("**可信文件路径（files.trusted_paths）**")
            trusted = st.text_area(
                "每行一条路径",
                value="\n".join(settings.get("files", {}).get("trusted_paths", [])),
                height=120,
                key="trusted_paths",
            )
            st.markdown("**写入黑名单（files.block_write）**")
            block_write = st.text_area(
                "每行一条 glob 规则",
                value="\n".join(settings.get("files", {}).get("block_write", [])),
                height=120,
                key="block_write",
            )

        if st.button("💾 保存 settings.json", use_container_width=True):
            settings["shell"]["allow"] = [l.strip() for l in allow_list.splitlines() if l.strip()]
            settings["shell"]["block"] = [l.strip() for l in block_list.splitlines() if l.strip()]
            settings["files"]["trusted_paths"] = [l.strip() for l in trusted.splitlines() if l.strip()]
            settings["files"]["block_write"] = [l.strip() for l in block_write.splitlines() if l.strip()]
            try:
                save_settings(settings)
                st.success("已保存")
            except Exception as e:
                st.error(f"保存失败：{e}")

        st.divider()
        st.markdown("**策略测试**")
        test_cmd = st.text_input("输入 shell 命令测试策略", placeholder="如：rm -rf /tmp/test")
        if test_cmd:
            r = assess_shell_policy(test_cmd)
            icons = {
                PolicyDecision.ALLOW:   ("✅", "green",  "白名单放行"),
                PolicyDecision.BLOCK:   ("🚫", "red",    "黑名单拦截"),
                PolicyDecision.CONFIRM: ("⚠️", "orange", "强制确认"),
                PolicyDecision.DEFER:   ("🔍", "blue",   "交给内置规则判断"),
            }
            icon, color, label = icons.get(r.decision, ("❓", "gray", "未知"))
            st.markdown(f"**{icon} {label}**  \n`{r.reason}`")

        test_path = st.text_input("输入文件路径测试策略", placeholder="如：/etc/hosts")
        if test_path:
            r = assess_file_policy(test_path)
            icons = {
                PolicyDecision.ALLOW:   ("✅", "green",  "可信路径放行"),
                PolicyDecision.BLOCK:   ("🚫", "red",    "写入黑名单拦截"),
                PolicyDecision.CONFIRM: ("⚠️", "orange", "强制确认"),
                PolicyDecision.DEFER:   ("🔍", "blue",   "交给内置规则判断"),
            }
            icon, color, label = icons.get(r.decision, ("❓", "gray", "未知"))
            st.markdown(f"**{icon} {label}**  \n`{r.reason}`")

# ────────────────────────────────────────────────────────────
# Tab 3 — 三层安全架构
# ────────────────────────────────────────────────────────────
with tab3:
    st.subheader("三层安全架构")

    st.markdown("""
每次工具调用经过三层安全检查，**优先级从高到低**：
""")

    st.markdown("""
| 层级 | 模块 | 规则来源 | 决策 | 可绕过？ |
|------|------|---------|------|---------|
| **1. Hooks** | `src/hooks.py` | 代码注册的回调 | 返回 False → 拦截 | 重启才能移除 |
| **2. Policy** | `src/security.py` | `~/.harness/settings.json` | BLOCK→拒绝 / ALLOW→放行 / DEFER→下一层 | 编辑 settings.json |
| **3. Builtin** | `src/permissions.py` | 硬编码正则规则 | 风险→询问用户 | `--yolo` 模式跳过 |
""")

    st.divider()
    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("#### 正常执行路径")
        st.code("""
工具调用: run_shell("git status")

① hooks.run_pre() → allowed=True ✅
② assess_policy()
   → 匹配白名单 "git *"
   → PolicyDecision.ALLOW ✅
   （跳过 permissions 层）
③ 工具执行: git status
④ hooks.run_post() → 结果写入 audit.log
""", language="text")

    with col2:
        st.markdown("#### 危险命令路径")
        st.code("""
工具调用: run_shell("rm -rf /")

① hooks.run_pre() → allowed=True ✅
② assess_policy()
   → 匹配黑名单 "rm -rf *"
   → PolicyDecision.BLOCK 🚫
   → "[已拦截：策略禁止...]"
   （直接返回，不执行工具）
""", language="text")

    st.divider()
    st.markdown("#### 与 Step 6 的对比")
    st.table({
        "特性": [
            "规则来源",
            "用户可配置",
            "运行时可扩展",
            "绕过方式",
            "审计记录",
        ],
        "Step 6 (permissions.py)": [
            "硬编码正则",
            "❌ 需改代码",
            "❌",
            "--yolo 跳过询问",
            "❌ 无",
        ],
        "Step 11 (hooks + security)": [
            "settings.json + 代码注册",
            "✅ 编辑 JSON",
            "✅ register_pre/post",
            "BLOCK 无法绕过；DEFER 可 --yolo",
            "✅ audit.log 完整记录",
        ],
    })

# ────────────────────────────────────────────────────────────
# Tab 4 — 审计日志
# ────────────────────────────────────────────────────────────
with tab4:
    st.subheader("审计日志浏览")

    try:
        from src.hooks import audit_log_path
        alog = audit_log_path()
        st.caption(f"日志文件：`{alog}`")

        if not alog.exists():
            st.info("审计日志为空。运行 CLI 并执行几条命令后再查看。")
            st.code("python -m src.main\n> 列出当前目录文件", language="bash")
        else:
            lines = alog.read_text(encoding="utf-8", errors="replace").splitlines()
            st.success(f"共 {len(lines)} 条记录")

            filter_phase = st.radio("过滤", ["全部", "PRE", "POST", "HOOK_ERROR"], horizontal=True)
            limit = st.slider("显示最近 N 条", 10, 200, 50)

            filtered = [l for l in lines if filter_phase == "全部" or filter_phase in l]
            filtered = filtered[-limit:]

            for line in reversed(filtered):
                if "HOOK_ERROR" in line:
                    st.error(line)
                elif "PRE " in line:
                    st.markdown(f"🔵 `{line}`")
                elif "POST " in line:
                    st.markdown(f"🟢 `{line}`")
                else:
                    st.text(line)

            if st.button("🗑 清空审计日志"):
                alog.write_text("", encoding="utf-8")
                st.success("已清空")
                st.rerun()
    except Exception as e:
        st.error(f"读取审计日志失败：{e}")
