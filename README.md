# Harness — 极简 Coding Agent

> 一个从零搭建的 AI Coding Agent，设计对标 Claude Code，使用 Python + 阿里云通义千问 API 实现。

[![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Steps](https://img.shields.io/badge/Steps-0--11-orange)](PROGRESS.md)

---

## 目录

- [项目简介](#项目简介)
- [架构总览](#架构总览)
- [功能特性](#功能特性)
- [快速开始](#快速开始)
- [项目结构](#项目结构)
- [核心模块说明](#核心模块说明)
- [CLI 命令速查](#cli-命令速查)
- [教学仪表盘](#教学仪表盘)
- [配置说明](#配置说明)
- [开发记录](#开发记录)
- [技术栈](#技术栈)

---

## 项目简介

**Harness** 是一个逐步构建的极简 Coding Agent，教学目标是完整还原 Claude Code 的核心架构。

项目采用"逐步封版"的开发模式：每个 Step 都是独立可运行的版本，配有 Streamlit 仪表盘页面，可以实时观察每个组件的工作原理。整个项目分 12 个步骤完整实现了 Agent 所需的所有核心能力。

**技术路线：**
- LLM 引擎：阿里云通义千问（`qwen-plus`），通过 OpenAI 兼容接口调用
- 语言：Python 3.11+
- 终端 UI：[Rich](https://github.com/Textualize/rich)
- 教学仪表盘：[Streamlit](https://streamlit.io/)

---

## 架构总览

```
用户输入（CLI / --prompt）
       ↓
   src/cli.py          ← REPL + 内置命令 + 安全确认
       ↓
   src/agent.py        ← 主循环（while True + 工具调用闭环）
       ↓
 ┌─────────────────────────────────────────────┐
 │               每轮工具调用                   │
 │  ① src/hooks.py     pre_tool_use hooks      │
 │  ② src/security.py  Policy 层（settings）   │
 │  ③ src/permissions.py 内置安全规则           │
 │  ④ src/tools.py     实际执行工具             │
 │  ⑤ src/hooks.py     post_tool_use hooks     │
 └─────────────────────────────────────────────┘
       ↓
   src/client.py       ← Qwen API（含流式 + 重试）
       ↓
   src/prompt.py       ← 系统提示词组装（记忆 + Git + CLAUDE.md）
```

### 三层上下文管理

```
Token 用量监控
  ├── Tier 0：工具结果预览截断（>3000 字符只存预览，完整内容缓存）
  ├── Tier 1：read_tool_result 按需懒加载（避免重新执行工具）
  └── Tier 2：LLM 历史摘要压缩（>80% 上下文时自动触发）
```

---

## 功能特性

### Agent 核心
- **工具调用闭环**：read_file / write_file / edit_file / run_shell / grep_search / list_files / read_tool_result
- **流式输出**：token 级实时打印，`StreamPrinter` + `thinking_spinner`
- **精准文件编辑**：`edit_file` 唯一性校验 + 自动缩进对齐，拒绝"盲目覆盖"
- **搜索导航**：`grep_search`（优先 ripgrep，降级为 Python re）+ `list_files`（自动过滤 .git/.venv 等）

### 可靠性
- **指数退避重试**：429 / 5xx / 网络超时自动重试，最多 4 次，上限 60s 等待
- **上下文压缩**：超出 80% 上下文时自动调用 LLM 摘要旧消息，保留最近 6 条
- **Lazy Expansion**：大工具结果只在历史中保留预览，完整内容按需懒加载

### 安全防护（三层）
| 层级 | 模块 | 规则来源 | 可绕过？ |
|------|------|---------|---------|
| Hooks 拦截 | `src/hooks.py` | 代码注册 | 仅重启可移除 |
| Policy 策略 | `src/security.py` | `~/.harness/settings.json` | 编辑 JSON |
| 内置规则 | `src/permissions.py` | 硬编码正则 | `--yolo` 跳过 |

### 持久化
- **会话持久化**：`~/.harness/sessions/` JSON 存储，`--resume` 跨会话续接
- **跨会话记忆**：`~/.harness/memory/MEMORY.md`，四类（user / feedback / project / reference），支持 LLM 自动提取
- **审计日志**：`~/.harness/audit.log`，完整记录每次工具调用

---

## 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone https://github.com/petit-nicolas/my_harness.git
cd my_harness

# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置 API Key

在项目根目录创建 `.ENV` 文件：

```bash
Ali_API_KEY=sk-your-dashscope-api-key-here
```

> 阿里云 DashScope API Key 申请：https://dashscope.console.aliyun.com/

### 3. 验证连接

```bash
# 测试 API 连接
python scripts/test_connection.py

# 测试工具调用
python scripts/test_tool_calling.py
```

### 4. 启动 Agent

```bash
# 交互式 REPL（推荐）
python -m src.main

# 单次执行模式
python -m src.main --prompt "帮我列出当前目录的 Python 文件"

# 指定工作目录
python -m src.main --cwd /path/to/your/project

# 恢复历史会话
python -m src.main --sessions           # 查看历史
python -m src.main --resume <id>        # 恢复指定会话

# 跳过安全确认（谨慎）
python -m src.main --yolo
```

### 5. 启动教学仪表盘

```bash
streamlit run dashboard/app.py
# 浏览器打开 http://localhost:8501
```

---

## 项目结构

```
harness/
├── src/                        # Agent 核心代码
│   ├── main.py                 # 程序入口
│   ├── cli.py                  # CLI / REPL 界面
│   ├── agent.py                # Agent 主循环
│   ├── client.py               # Qwen API 客户端（单例 + 重试）
│   ├── prompt.py               # System prompt 组装器
│   ├── system_prompt.md        # System prompt 模板
│   ├── tools.py                # 工具注册表 + 执行器 + Lazy Expansion
│   ├── permissions.py          # 内置安全规则（硬编码正则）
│   ├── security.py             # Policy 层（settings.json 规则）
│   ├── hooks.py                # Hooks 扩展机制（pre/post_tool_use）
│   ├── retry.py                # 指数退避重试
│   ├── ui.py                   # Rich 终端 UI 组件
│   ├── session.py              # 会话持久化（JSON 存取）
│   └── memory.py               # 跨会话记忆系统（MEMORY.md）
│
├── dashboard/                  # Streamlit 教学仪表盘
│   ├── app.py                  # 仪表盘入口 + 导航
│   ├── components/
│   │   └── shared.py           # 公共 UI 组件
│   └── pages/
│       ├── step0_overview.py   # 项目概览
│       ├── step1_api.py        # API 连接与工具调用
│       ├── step2_prompt.py     # 提示词组装可视化
│       ├── step3_agent.py      # Agent 主循环演示
│       ├── step4_edit.py       # edit_file 精准编辑
│       ├── step5_search.py     # grep_search + list_files
│       ├── step6_safety.py     # 安全确认机制
│       ├── step7_stream.py     # 流式输出
│       ├── step8_retry.py      # 重试 + 上下文压缩 + Lazy Expansion
│       ├── step9_session.py    # 会话持久化
│       ├── step10_memory.py    # 跨会话记忆
│       └── step11_hooks.py     # Hooks + 高级安全
│
├── scripts/                    # 独立验证脚本
│   ├── test_connection.py      # API 连接测试
│   └── test_tool_calling.py    # 工具调用测试
│
├── res/                        # 参考资料（PDF 研究文档）
├── PLAN.md                     # 完整开发计划
├── PROGRESS.md                 # 进度追踪
├── CLAUDE.md                   # 项目约定（注入 agent 提示词）
├── requirements.txt
└── .gitignore
```

---

## 核心模块说明

### `src/agent.py` — Agent 主循环

```python
run_agent(
    session,         # AgentSession（消息历史 + token 用量 + 权限缓存）
    user_input,      # 本轮用户输入
    stream=True,     # 流式 / 非流式
    on_text_chunk,   # 流式文本 delta 回调
    on_tool_call,    # 工具触发回调
    on_tool_result,  # 工具结果回调
    confirm_fn,      # 危险操作确认回调（None = --yolo）
    stop_event,      # Ctrl+C 中断信号
)
```

**循环结构：**

```
build_system_prompt()
  → while True:
      [可选] should_compact() → compact_context()
      chat(messages, tools, stream=True/False)
      if tool_calls:
          ① hooks.run_pre()
          ② assess_policy()     # settings.json
          ③ assess_tool_call()  # 内置规则
          run_tool()
          hooks.run_post()
          _truncate_for_history()  # Lazy Expansion
      else:
          break → 返回最终文本
```

### `src/tools.py` — 工具系统

| 工具 | 说明 |
|------|------|
| `read_file` | 读取文件，超 50,000 字自动截断 |
| `write_file` | 写入/新建文件 |
| `edit_file` | 唯一性精准替换，自动对齐缩进 |
| `run_shell` | 执行 shell 命令 |
| `grep_search` | 正则搜索（ripgrep 优先，降级 Python re） |
| `list_files` | 目录树，自动过滤无关目录 |
| `read_tool_result` | 按需懒加载被截断的历史工具结果 |

### `src/memory.py` — 记忆系统

四类记忆存储于 `~/.harness/memory/MEMORY.md`：

| 类型 | 用途 | 示例 |
|------|------|------|
| `user` | 个人偏好、习惯 | "用户不喜欢冗长注释" |
| `feedback` | 对 agent 行为的反馈 | "解释太长，直接给代码" |
| `project` | 项目技术栈、路径 | "/Users/foo/api 使用 FastAPI" |
| `reference` | 通用技术知识 | "Python 3.10+ 用 X\|Y 代替 Optional" |

每次启动自动注入到 system prompt，让 agent 记住跨会话积累的上下文。

### `src/hooks.py` — Hooks 扩展

```python
from src.hooks import HOOKS, HookEvent

# 拦截危险命令
@HOOKS.pre_tool_use
def block_sudo(event: HookEvent) -> bool | None:
    if event.tool_name == "run_shell":
        if "sudo" in event.arguments.get("command", ""):
            return False   # 阻止执行
    return True

# 记录工具结果
@HOOKS.post_tool_use
def log_result(event: HookEvent) -> str | None:
    print(f"[{event.tool_name}] → {len(event.result or '')} chars")
    return None   # 不修改结果
```

---

## CLI 命令速查

在 REPL 中输入以下命令（以 `/` 开头）：

| 命令 | 说明 |
|------|------|
| `/help` | 显示所有命令 |
| `/clear` | 清空对话历史 + 工具缓存 + 统计 |
| `/cost` | 显示 Token 用量明细 |
| `/compact` | 手动压缩历史（LLM 摘要旧消息） |
| `/save` | 保存当前会话到磁盘 |
| `/sessions` | 列出最近 10 条历史会话 |
| `/load <id>` | 恢复指定会话（热替换，不退出） |
| `/remember [cat] <text>` | 手动保存记忆 |
| `/memories [query]` | 浏览/搜索记忆库 |
| `/forget <id>` | 删除指定记忆 |
| `/extract` | LLM 从当前对话自动提取记忆 |
| `/stats` | 显示工具调用统计 |
| `/exit` | 退出（非空会话自动保存） |

**快捷键：**
- `Ctrl+C`（任务运行中）：中断当前工具调用
- `Ctrl+C`（空闲中）：自动保存会话后退出
- `Ctrl+D`：同上

---

## 教学仪表盘

启动后在浏览器打开 `http://localhost:8501`：

```bash
streamlit run dashboard/app.py
```

每个 Step 对应一个独立页面，提供：
- 该步骤的核心概念讲解
- 关键代码片段展示
- 交互式功能演示（可直接操作）
- 与 Claude Code 的设计对比

| 页面 | 内容 |
|------|------|
| Step 0 — 项目概览 | 架构图、进度追踪 |
| Step 1 — API 连接 | Qwen API 测试、工具调用验证 |
| Step 2 — 提示词 | System prompt 组装可视化 |
| Step 3 — Agent 循环 | 交互式 Agent 对话 |
| Step 4 — 精准编辑 | edit_file 唯一性 + 缩进演示 |
| Step 5 — 搜索导航 | grep_search + list_files |
| Step 6 — 安全确认 | 危险命令识别 + 确认流程 |
| Step 7 — 流式输出 | 实时 token 展示 |
| Step 8 — 可靠性 | 重试 + 上下文压缩 + Lazy Expansion |
| Step 9 — 会话持久化 | 历史会话浏览与恢复 |
| Step 10 — 记忆系统 | 四类记忆管理 |
| Step 11 — Hooks | 规则配置 + 审计日志 |

---

## 配置说明

### `.ENV` — API Key

```
Ali_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### `~/.harness/settings.json` — 安全策略

首次运行自动创建，可手动编辑或通过仪表盘修改：

```json
{
  "version": 1,
  "shell": {
    "allow": [
      "git *", "pytest *", "python *", "pip *",
      "ls *", "cat *", "echo *", "rg *"
    ],
    "block": [],
    "always_confirm": []
  },
  "files": {
    "trusted_paths": [],
    "block_write": [
      "/etc/*", "/usr/*", "~/.ssh/*", "~/.aws/credentials"
    ]
  }
}
```

**策略优先级：**
1. `files.block_write` / `shell.block` → 强制拒绝（`--yolo` 也无法绕过）
2. `shell.allow` / `files.trusted_paths` → 直接放行
3. 无匹配 → 交给内置安全规则判断

### `CLAUDE.md` — 项目约定

放在工作目录根目录，agent 启动时自动读取并注入提示词：

```markdown
# 项目约定

## 技术栈
- Python 3.12 + FastAPI

## 代码规范
- 使用 ruff 格式化
- 类型注解必须完整
```

---

## 开发记录

每个步骤均有 Git tag 标记，可通过 `git checkout step-N` 查看该阶段的完整代码：

| Tag | 内容 |
|-----|------|
| `step-0` | 项目骨架 + Cursor 规则 + Streamlit 仪表盘框架 |
| `step-1` | Qwen API 客户端 + 工具调用验证 |
| `step-2` | System prompt 模板 + 组装器 + CLAUDE.md 注入 |
| `step-3` | Agent 主循环 + 工具注册表 + CLI REPL |
| `step-4` | `edit_file` 精准编辑（唯一性校验 + 缩进对齐） |
| `step-5` | `grep_search` + `list_files`（ripgrep/re 双路） |
| `step-6` | 安全确认机制 + `--yolo` 模式 + PermissionCache |
| `step-7` | 流式输出（`_collect_stream` + `StreamPrinter`） |
| `step-8` | 重试 + 上下文压缩 + Lazy Expansion 三层防御 |
| `step-9` | 会话持久化（JSON + `--resume` + 自动保存） |
| `step-10` | 跨会话记忆（MEMORY.md + `/extract` LLM 提取） |
| `step-11` | Hooks 扩展 + security.py Policy 层 + 审计日志 |

详细进度见 [PROGRESS.md](PROGRESS.md)。

---

## 技术栈

| 组件 | 库/工具 | 版本 |
|------|---------|------|
| LLM API | openai (DashScope 兼容模式) | ≥1.30.0 |
| 环境变量 | python-dotenv | ≥1.0.0 |
| 终端 UI | rich | ≥13.7.0 |
| 教学仪表盘 | streamlit | ≥1.35.0 |
| Python | CPython | ≥3.11 |

---

## License

MIT
