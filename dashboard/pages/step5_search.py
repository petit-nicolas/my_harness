"""
Step 5 — 文件搜索与导航页
可视化体验：grep_search 正则搜索 + list_files 目录树
"""
import sys
import pathlib

ROOT = pathlib.Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st
from src.tools import run_tool

# ── 页面初始化 ─────────────────────────────────────────────
st.title("Step 5 · 搜索与导航工具")
st.caption("能力阶段 — grep_search 代码搜索 + list_files 目录导航，让 Agent 快速理解陌生项目")

with st.expander("学习目标", expanded=False):
    st.markdown("""
- 理解 AI Agent 为何需要专用搜索工具（而不是盲目全文读取）
- 掌握 `grep_search` 的正则搜索与 `include` 过滤用法
- 观察 `list_files` 的黑名单过滤机制（.git、.venv 等自动剔除）
- 体验 Agent "进入陌生项目 → list_files → grep_search 定位" 的典型工作流
""")

tab1, tab2, tab3 = st.tabs(["🔍 grep_search", "📁 list_files", "🔄 典型工作流"])

# ── Tab 1：grep_search ─────────────────────────────────────
with tab1:
    st.subheader("grep_search — 正则代码搜索")

    col_l, col_r = st.columns([1, 1])
    with col_l:
        pattern = st.text_input("搜索 pattern（正则）", value=r"def _\w+", key="grep_pat")
        search_path = st.text_input("搜索路径", value="src", key="grep_path")
        col_a, col_b = st.columns(2)
        with col_a:
            case_sens = st.checkbox("区分大小写", value=True, key="grep_case")
        with col_b:
            include = st.text_input("文件过滤 glob", value="*.py", key="grep_include",
                                    help="如 *.py、*.md、*.{ts,tsx}")

    with col_r:
        st.markdown("**常用搜索 pattern 参考**")
        st.markdown(r"""
| 目标 | Pattern |
|------|---------|
| 所有函数定义 | `def \w+` |
| 所有类 | `^class \w+` |
| TODO / FIXME | `(TODO|FIXME)` |
| import 某个模块 | `from src\.tools import` |
| 错误/异常 | `raise|except` |
""")

    if st.button("执行 grep_search", type="primary", use_container_width=True, key="grep_btn"):
        with st.spinner("搜索中..."):
            result = run_tool("grep_search", {
                "pattern": pattern,
                "path": str(ROOT / search_path) if not pathlib.Path(search_path).is_absolute() else search_path,
                "case_sensitive": case_sens,
                "include": include,
            })
        st.session_state["grep_result"] = result

    result = st.session_state.get("grep_result", "")
    if result:
        lines = [l for l in result.split("\n") if l.strip()]
        is_error = result.startswith("错误") or result.startswith("（")

        if is_error:
            st.info(result)
        else:
            st.success("找到 " + str(len(lines)) + " 处匹配")
            # 转换为表格展示
            rows = []
            for line in lines:
                parts = line.split(":", 2)
                if len(parts) == 3:
                    rows.append({"文件": parts[0], "行号": parts[1], "内容": parts[2].strip()})
                else:
                    rows.append({"文件": line, "行号": "", "内容": ""})

            # 展示为代码块（保留文件路径高亮）
            # 截断绝对路径，只显示相对于 ROOT 的部分
            display_lines = []
            for r_item in rows:
                try:
                    rel = str(pathlib.Path(r_item["文件"]).relative_to(ROOT))
                except ValueError:
                    rel = r_item["文件"]
                display_lines.append(rel + ":" + r_item["行号"] + "  " + r_item["内容"])

            st.code("\n".join(display_lines), language="text")

# ── Tab 2：list_files ──────────────────────────────────────
with tab2:
    st.subheader("list_files — 目录文件树")

    col_l2, col_r2 = st.columns([1, 1])
    with col_l2:
        list_path = st.text_input("目录路径", value=".", key="list_path")
        list_pattern = st.text_input("文件过滤 glob", value="", placeholder="留空=全部文件，如 *.py", key="list_pat")

    with col_r2:
        st.markdown("**自动过滤的目录**")
        excludes = [".git", ".venv", "venv", "__pycache__", "node_modules",
                    ".mypy_cache", ".pytest_cache", ".cursor", "dist", "build"]
        st.code("\n".join(excludes), language="text")

    if st.button("执行 list_files", type="primary", use_container_width=True, key="list_btn"):
        with st.spinner("列目录中..."):
            abs_path = str(ROOT / list_path) if not pathlib.Path(list_path).is_absolute() else list_path
            result2 = run_tool("list_files", {
                "path": abs_path,
                "pattern": list_pattern,
            })
        st.session_state["list_result"] = result2
        st.session_state["list_root"] = abs_path

    result2 = st.session_state.get("list_result", "")
    list_root_str = st.session_state.get("list_root", str(ROOT))
    if result2:
        if result2.startswith("错误") or result2.startswith("（"):
            st.info(result2)
        else:
            files = [l for l in result2.split("\n") if l.strip() and not l.startswith("[")]
            truncated = "[已截断" in result2
            st.success("找到 " + str(len(files)) + " 个文件" + ("（已截断）" if truncated else ""))

            # 按目录分组显示
            dir_map: dict[str, list[str]] = {}
            for f in files:
                p = pathlib.Path(f)
                d = str(p.parent) if p.parent != pathlib.Path(".") else "(根目录)"
                dir_map.setdefault(d, []).append(p.name)

            for d_name, fnames in sorted(dir_map.items()):
                with st.expander("📂 " + d_name + "  (" + str(len(fnames)) + " 个文件)", expanded=(d_name == "(根目录)")):
                    st.code("\n".join(sorted(fnames)), language="text")

# ── Tab 3：典型工作流 ──────────────────────────────────────
with tab3:
    st.subheader("Agent 进入陌生项目的典型工作流")
    st.markdown("""
当 Agent 收到"帮我修改 foo 功能"这类任务，且对项目结构不熟时，标准流程是：

```
1. list_files(path=".")          → 了解目录结构，定位相关模块
2. list_files(pattern="*.py")    → 确认 Python 文件分布
3. grep_search("class Foo")      → 找到目标类定义
4. read_file("src/foo.py")       → 读取具体文件
5. edit_file / write_file        → 执行修改
```

这个流程的核心价值：**最小化 Token 消耗**，只读真正需要的内容。
""")

    st.divider()
    st.markdown("#### 在本项目上演示这个流程")

    if st.button("一键演示完整工作流", use_container_width=True):
        st.markdown("**Step 1：list_files — 了解项目结构**")
        r_list = run_tool("list_files", {"path": str(ROOT), "pattern": "*.py"})
        py_files = [l for l in r_list.split("\n") if l.strip()]
        st.code("\n".join(py_files[:15]), language="text")
        if len(py_files) > 15:
            st.caption("（仅显示前 15 个）")

        st.markdown("**Step 2：grep_search — 找到所有已注册工具名**")
        r_grep = run_tool("grep_search", {
            "pattern": r'"name":\s*"[a-z_]+"',
            "path": str(ROOT / "src" / "tools.py"),
        })
        grep_lines = [l for l in r_grep.split("\n") if l.strip()]
        display = []
        for gl in grep_lines:
            parts = gl.split(":", 2)
            if len(parts) == 3:
                try:
                    rel = str(pathlib.Path(parts[0]).relative_to(ROOT))
                except ValueError:
                    rel = parts[0]
                display.append(rel + ":" + parts[1] + "  " + parts[2].strip())
            else:
                display.append(gl)
        st.code("\n".join(display), language="text")

        st.success("✓ Agent 已定位到 " + str(len(grep_lines)) + " 个工具注册条目，无需读取整个文件")
