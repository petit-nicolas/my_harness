"""
Step 4 — edit_file 精准替换页
可视化体验：old_string 唯一性校验 + diff 对比 + 缩进自动对齐演示
"""
import sys
import pathlib
import difflib
import tempfile

ROOT = pathlib.Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st
from src.tools import run_tool

# ── 页面初始化 ─────────────────────────────────────────────
st.title("Step 4 · edit_file 精准替换")
st.caption("能力阶段 — 理解为什么 AI 修改文件需要唯一性校验，而不是简单的全文覆盖")

with st.expander("学习目标", expanded=False):
    st.markdown("""
- 理解 `edit_file` 的设计哲学：只改必须改的部分，减少意外覆盖风险
- 掌握 `old_string` 唯一性约束：匹配 0 次 / 多次时的错误处理
- 观察缩进自动对齐机制：`new_string` 无需手动补前导空白
- 与 `write_file` 对比：局部修改 vs 全文覆盖各自的适用场景
""")

tab1, tab2, tab3 = st.tabs(["🔧 交互式体验", "📐 缩进对齐演示", "⚖️ edit vs write 对比"])

# ── Tab 1：交互式体验 ──────────────────────────────────────
with tab1:
    st.subheader("实时 edit_file 体验")
    st.info("在下方编辑文件内容和替换参数，观察唯一性校验和替换结果")

    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("**原始文件内容**")
        default_content = '''\
def greet(name: str) -> str:
    message = "hello"
    print(message)
    return message
'''
        file_content = st.text_area(
            "文件内容",
            value=default_content,
            height=180,
            label_visibility="collapsed",
        )

        st.markdown("**old_string**（要被替换的内容）")
        old_string = st.text_area(
            "old_string",
            value='    message = "hello"',
            height=80,
            label_visibility="collapsed",
        )

        st.markdown("**new_string**（替换后的内容）")
        new_string = st.text_area(
            "new_string",
            value='message = f"Hello, {name}!"',
            height=80,
            help="无需手动添加缩进，工具会自动对齐",
            label_visibility="collapsed",
        )

    with col_right:
        st.markdown("**执行结果**")

        if st.button("执行 edit_file", type="primary", use_container_width=True):
            # 写临时文件
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".py", delete=False, encoding="utf-8"
            ) as f:
                f.write(file_content)
                tmp_path = f.name

            result = run_tool("edit_file", {
                "path": tmp_path,
                "old_string": old_string,
                "new_string": new_string,
            })

            st.session_state["edit_result"] = result
            st.session_state["edit_original"] = file_content
            if "已替换" in result:
                st.session_state["edit_new_content"] = pathlib.Path(tmp_path).read_text(encoding="utf-8")
            else:
                st.session_state["edit_new_content"] = None

        result = st.session_state.get("edit_result", "")
        original = st.session_state.get("edit_original", "")
        new_content = st.session_state.get("edit_new_content", None)

        if result:
            if "已替换" in result:
                st.success(result)
            else:
                st.error(result)

        if new_content:
            st.markdown("**替换后文件内容**")
            st.code(new_content, language="python")

            st.markdown("**Diff 对比**")
            diff_lines = list(difflib.unified_diff(
                original.splitlines(keepends=True),
                new_content.splitlines(keepends=True),
                fromfile="原始文件",
                tofile="替换后",
                lineterm="",
            ))
            if diff_lines:
                diff_text = "".join(diff_lines)
                st.code(diff_text, language="diff")
            else:
                st.info("内容无变化")

    # 三种场景说明
    st.divider()
    st.markdown("#### 三种返回场景")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.error("**匹配 0 次**\n\nold_string 与文件内容不完全一致（空格/换行差异）\n\n→ 先用 read_file 确认实际内容")
    with c2:
        st.warning("**匹配 N 次**\n\nold_string 太短，在多处出现\n\n→ 扩大 old_string 范围，加入更多上下文行")
    with c3:
        st.success("**匹配 1 次**\n\n唯一定位，安全替换\n\n→ 工具执行替换并返回确认")

# ── Tab 2：缩进对齐演示 ────────────────────────────────────
with tab2:
    st.subheader("缩进自动对齐")
    st.markdown("""
`edit_file` 会提取 `old_string` 首行的前导空白，并将其应用到 `new_string` 的每一行。
这意味着你写 `new_string` 时**不需要手动补缩进**。
""")

    indent_cases = [
        {
            "title": "场景 A — 替换类方法体",
            "original": "class MyClass:\n    def process(self):\n        pass\n",
            "old": "        pass",
            "new": "result = self._compute()\nreturn result",
            "note": "new_string 无缩进 → 工具自动补 8 空格",
        },
        {
            "title": "场景 B — 替换顶层函数体",
            "original": "def helper():\n    x = 1\n    return x\n",
            "old": "    x = 1\n    return x",
            "new": "x = len(self.data)\nreturn x * 2",
            "note": "new_string 无缩进 → 工具自动补 4 空格",
        },
    ]

    for case in indent_cases:
        with st.expander(case["title"], expanded=True):
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("**原始文件**")
                st.code(case["original"], language="python")
                st.markdown(f"**old_string** `→ {repr(case['old'][:30])}...`")
                st.markdown("**new_string（无缩进）**")
                st.code(case["new"], language="python")

            with col_b:
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".py", delete=False, encoding="utf-8"
                ) as f:
                    f.write(case["original"])
                    tmp = f.name

                r = run_tool("edit_file", {
                    "path": tmp,
                    "old_string": case["old"],
                    "new_string": case["new"],
                })
                after = pathlib.Path(tmp).read_text(encoding="utf-8") if "已替换" in r else case["original"]

                st.markdown("**替换后文件**")
                st.code(after, language="python")
                st.caption(case["note"])

                if "已替换" in r:
                    st.success(r)

# ── Tab 3：edit vs write 对比 ─────────────────────────────
with tab3:
    st.subheader("edit_file vs write_file：如何选择")

    st.markdown("""
| 场景 | 推荐工具 | 原因 |
|------|----------|------|
| 修改函数中的一行逻辑 | `edit_file` | 只改必要部分，不影响其余代码 |
| 新增一个导入语句 | `edit_file` | 精准定位现有 import 块末尾后插入 |
| 重命名一个变量（多处） | `edit_file` × N | 每次替换唯一上下文，逐一确认 |
| 新建文件 | `write_file` | 文件不存在，直接写入 |
| 整体重构，结构变化大 | `write_file` | 局部替换上下文难以唯一定位时 |
| 配置文件完全替换 | `write_file` | 内容短且全量替换更安全 |
""")

    st.divider()
    st.markdown("#### 为什么 AI 代码编辑不应该总是用 write_file？")
    col_w, col_e = st.columns(2)
    with col_w:
        st.error("""**write_file 的风险**

- 需要把整个文件内容传给 AI → Token 消耗翻倍
- AI 在重写时可能引入意外空格、注释变动
- 文件很长时截断风险高
- 无法表达"只改这一处"的意图
""")
    with col_e:
        st.success("""**edit_file 的优势**

- old_string + new_string 只传变化部分 → 省 Token
- 唯一性校验防止模糊替换
- diff 清晰，可审查
- 自动缩进对齐，减少格式错误
""")
