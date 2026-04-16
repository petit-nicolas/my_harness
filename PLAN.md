# 极简 Coding Agent (Harness) 实现计划

> **目标**：从零开始复现类似 Claude Code 的极简 Coding Agent，使用千问 API 作为大模型引擎
> **语言**：Python 3.11+
> **参考**：`res/` 目录下 12 份 Claude Code 架构研究文档

---

## 整体架构

```
用户输入 → 提示词编排 → Agent 循环 → 工具执行 → 结果输出 → 等待/退出
                                    ↑___________________________|
```

全程分为 **5 个阶段**、**12 个步骤**，逐步递进：

| 阶段 | 目标 | 代码量估算 | 步骤 |
|------|------|-----------|------|
| 准备阶段 | 项目规则、骨架、仪表盘框架 | ~200 行 | Step 0 |
| 骨架阶段 | 跑通 Agent 基本循环 | ~500 行 | Step 1-3 |
| 能力阶段 | 补全工具集与安全机制 | ~1500 行 | Step 4-6 |
| 体验阶段 | 流式输出 + 错误处理 + 会话 | ~3000 行 | Step 7-9 |
| 进阶阶段 | 记忆 + 扩展性 | ~5000 行 | Step 10-11 |

---

## 代码管理策略

本项目是**教学框架**，每个 Step 完成后都是一个可独立运行和体验的封版。

### 版本管理

- 使用 Git 管理代码，每个 Step 完成后打 tag：`step-0`、`step-1`、...、`step-11`
- 用户可通过 `git checkout step-3` 回到任意阶段的代码快照
- 每个 tag 对应一个可运行的完整项目

### 子任务推进机制

- 每个 Step 拆分为 2-5 个子任务，编号 `X.Y`（如 `1.2`）
- 逐个推进，完成一个后暂停，等用户确认再继续
- 子任务进度实时记录在 `PROGRESS.md` 中
- 该机制由 `.cursor/rules/task-protocol.mdc` 约束，所有对话自动遵循

### 封版流程

```
子任务全部完成 → 代码可运行 → Streamlit 页面可演示
  → git commit → git tag step-X → PROGRESS.md 标记封版
```

---

## 配套 UI 方案 — Streamlit 教学仪表盘

每个 Step 配备一个 Streamlit 页面，用于可视化体验该阶段的核心能力。

### 仪表盘结构

```
dashboard/
├── app.py                # 主入口，侧边栏导航
├── pages/
│   ├── step0_overview.py     # 项目概览 + 计划总览
│   ├── step1_api.py          # API 连通性测试 + Tool Calling 演示
│   ├── step2_prompt.py       # 提示词组装可视化，可编辑变量
│   ├── step3_agent.py        # Agent 循环流程图 + 实时对话
│   ├── step4_edit.py         # 编辑工具 diff 对比展示
│   ├── step5_search.py       # 搜索结果可视化
│   ├── step6_security.py     # 安全规则配置 + 拦截演示
│   ├── step7_stream.py       # 流式输出效果演示
│   ├── step8_compress.py     # 上下文压缩过程可视化
│   ├── step9_session.py      # 会话管理界面
│   ├── step10_memory.py      # 记忆检索与管理
│   └── step11_hooks.py       # Hooks 配置与日志查看
└── components/
    └── shared.py             # 共享 UI 组件（页头、状态栏等）
```

### 每个页面的标准结构

1. **学习目标**：该 Step 要掌握的核心概念（2-3 条）
2. **架构图**：该组件在整体架构中的位置
3. **交互演示**：可操作的功能体验区
4. **关键代码**：核心代码片段展示 + 注释说明
5. **参考文档**：对应的 `res/*.pdf` 链接

### 运行方式

```bash
streamlit run dashboard/app.py
```

---

## 准备阶段 — 项目基础设施

### Step 0：项目准备工作

**目标**：搭建项目管理基础设施 — Cursor 规则、Git 仓库、依赖管理、仪表盘骨架

**子任务**：

- **0.1** Cursor 规则与日志机制 — `.cursor/rules/` + `PROGRESS.md`（已完成）
- **0.2** 项目骨架搭建 — git init、`.gitignore`、`requirements.txt`、`src/` 目录结构
- **0.3** Streamlit 仪表盘骨架 — `dashboard/app.py` + 首页，验证 Streamlit 可运行

**产出文件**：
```
.cursor/rules/
├── project-overview.mdc
├── task-protocol.mdc
└── python-standards.mdc
.gitignore
requirements.txt
PROGRESS.md
dashboard/
├── app.py
└── pages/
    └── step0_overview.py
```

---

## 骨架阶段 — 跑通 Agent 基础

### Step 1：项目初始化 + 千问 API 对接

**目标**：建立项目脚手架，验证千问 API 可正常调用且支持 function calling

**实施要点**：

1. **初始化 Python 项目**
   - `requirements.txt` 管理依赖
   - 安装依赖：`openai`（Python 版 OpenAI SDK，直接对接千问）、`python-dotenv`
   - 推荐使用虚拟环境：`python -m venv .venv && source .venv/bin/activate`

2. **编写 API 客户端** (`src/client.py`)
   - 使用 `openai.OpenAI` 但指向千问 endpoint：`https://dashscope.aliyuncs.com/compatible-mode/v1`
   - 通过 `python-dotenv` 从 `.ENV` 读取 `Ali_API_KEY`
   - 默认模型：`qwen-plus` 或 `qwen-max`
   - 封装统一的 `chat()` 函数，调用者无需关心底层细节

3. **冒烟测试**
   - 直接发送一条 "你好" 验证连通性
   - 测试 tool calling：定义一个假工具 JSON Schema，验证模型能正确返回 tool call

**参考文档**：`res/1. 首页.pdf` — 千问与 OpenAI 协议的差异说明

**产出文件**：
```
src/
├── client.py      # 千问 API 封装客户端
└── main.py        # 项目入口（临时测试用）
.ENV               # API 密钥
requirements.txt
```

---

### Step 2：提示词编排系统

**目标**：构建一套动态组装系统提示词的机制，让 Agent 具备自我认知、环境感知和项目上下文理解能力

**实施要点**：

1. **编写系统提示词模板** (`src/system_prompt.md`)
   - Agent 角色定义：有能力的编码助手，不假设、不猜测
   - 工具使用规范：何时读文件、何时用 shell 等
   - 支持占位符动态注入：`{{cwd}}`、`{{date}}`、`{{platform}}`、`{{shell}}`、`{{git_context}}`
   - 支持项目上下文注入：`{{claude_md}}`

2. **编写提示词组装器** (`src/prompt.py`)
   - `build_system_prompt()` 组合：角色提示 + 工具说明 + 环境信息
   - `get_git_context()`：用 `subprocess` 检测 git 仓库，提取最近 3 条 git log
   - `load_claude_md()`：用 `pathlib.Path` 递归向上查找 `CLAUDE.md` 文件并加载

3. **CLAUDE.md 支持**
   - 若当前目录存在 `CLAUDE.md`，其内容注入系统提示最前面
   - 项目级自定义指令优先级高于全局默认

**关键设计**（来自 `res/3. 上下文.pdf`）：
- 系统提示应当**对模型而言始终如一**，避免随机扰动
- git 状态信息紧随 git 用户名之后，作为一个独立段落
- CLAUDE.md 通过插入到消息列表最前端传入，而不是拼接到系统提示末尾

**产出文件**：
```
src/
├── prompt.py          # 提示词组装逻辑
└── system_prompt.md   # 系统提示词模板
```

---

### Step 3：Agent 循环核心 + 基础 CLI

**目标**：实现 Agent Loop 核心 `while True` 循环 — 这是整个 Agent 的心跳，负责协调模型调用、工具执行与对话管理

**实施要点**：

1. **定义基础工具集** (`src/tools.py`)
   - `read_file`：用 `pathlib.Path.read_text()` 读取文件，返回内容
   - `write_file`：用 `Path.write_text()` 创建/覆盖文件
   - `run_shell`：用 `subprocess.run()` 执行 Shell 命令，捕获 stdout/stderr
   - 每个工具用 Python dict 描述 JSON Schema，符合 OpenAI function calling 格式
   - 单次读取内容上限 50,000 字符，超出时截断并提示

2. **实现 Agent 主循环** (`src/agent.py`)
   ```
   构建消息 → 调用 API → while True:
     解析响应 → 若有 tool_calls → 执行工具 → 追加结果 → continue
     若无 tool_calls → 输出文本 → break
   ```
   - 消息历史用 Python `list[dict]` 在内存中全程保留（含 tool results）
   - Token 用量统计（input/output），存入会话状态
   - 使用 `threading.Event` 配合 `signal.signal(SIGINT, ...)` 支持 Ctrl+C 中断

3. **实现基础 CLI 界面** (`src/cli.py`)
   - 基于内置 `readline` + `input()` 的 REPL 交互
   - 支持 `--prompt "..."` 单次执行模式（用 `argparse`）
   - 每次响应后展示耗时 + 费用估算

**关键设计**（来自 `res/2. 代理循环.pdf`）：
- 工具执行遵循"最小权限原则" — 确认后才执行危险操作
- 工具结果必须按照 `{"role": "tool", "tool_call_id": ..., "content": ...}` 格式追加到消息历史
- 当工具被用户拒绝时，返回 "User denied this action." 并继续循环

**产出文件**：
```
src/
├── agent.py    # Agent 主循环
├── tools.py    # 工具定义 + 执行器
└── cli.py      # CLI 界面
```

**阶段验收**：能够完整回答 "帮我分析 requirements.txt 的依赖"，Agent 自主调用 read_file 工具并给出总结

---

## 能力阶段 — 补全工具与安全机制

### Step 4：Search-and-Replace 精准编辑工具

**目标**：相比粗暴的全文件覆盖，search-and-replace 是更安全、更精准的代码编辑策略

**实施要点**：

1. **新增 `edit_file` 工具**
   - 参数：`file_path`、`old_string`、`new_string`
   - 唯一性校验：`old_string` 在文件中必须有且仅有一处匹配
   - 匹配数 = 0 → 报错 "String not found"
   - 匹配数 > 1 → 报错 "Found N matches, must be unique"
   - 匹配数 = 1 → 执行替换：`content.replace(old_string, new_string, 1)`

2. **自动保留缩进**
   - 检测 `old_string` 首行的前导空白（空格/Tab），应用到 `new_string` 每一行

3. **提示词引导**
   - 系统提示补充："优先使用 edit_file 进行小范围修改，仅当需要全文重写时才用 write_file"
   - 提示模型："修改前请先检查缩进风格是否一致，tabs/spaces 不要混用"

**关键设计**（来自 `res/5. 代码编辑.pdf`）：
- search-and-replace 策略的精髓是"最小变更"，减少模型出错的上下文范围
- 唯一性约束是核心安全保障，防止模型误改所有同名函数
- 可用 `content.count(old_string)` 快速计算匹配次数

**产出**：更新 `src/tools.py`

---

### Step 5：文件搜索与导航工具

**目标**：让 Agent 能够高效地在代码库中搜索内容和导航文件结构

**实施要点**：

1. **新增 `grep_search` 工具**
   - 通过 `subprocess.run()` 调用系统 `grep`（优先 `rg` ripgrep）
   - 参数：`pattern`（正则）、`path`（搜索根目录）、`include`（文件类型过滤，如 `*.py`）
   - 限制最多返回 100 条结果，超出时提示

2. **新增 `list_files` 工具**
   - 使用 `pathlib.Path.rglob()` 或内置 `glob.glob()` 实现
   - 自动排除 `__pycache__`、`.git`、`.venv`、`node_modules` 等目录
   - 限制最多返回 200 个路径

3. **提示词引导**
   - 系统提示补充："优先用 grep_search 搜索内容，而不是 run_shell('grep ...')"

**关键设计**（来自 `res/4. 工具.pdf`）：
- 专用工具 vs Shell 命令的权衡：专用工具有结构化输出、结果数量控制、更安全
- 工具描述要极度精炼，避免"废话"占用 Token

**产出**：更新 `src/tools.py`

---

### Step 6：安全确认机制 + 危险命令拦截

**目标**：防止 Agent 执行破坏性操作，在执行前给用户确认机会

**实施要点**：

1. **危险命令识别** (`src/permissions.py`)
   - 维护危险操作关键词列表：`rm`、强制 git 操作、`sudo`、`mkfs`、`dd`、`kill` 等约 10 类
   - 使用 `re.search(r'\brm\b', cmd)` 做正则边界匹配，避免误判

2. **交互式确认**
   - 检测到危险操作时，暂停并用 `input()` 提示用户输入 y/n
   - 已确认的路径缓存到会话中（Python `set`），避免重复确认

3. **`--yolo` 模式**
   - `argparse` 参数开启后跳过所有确认（适用于自动化场景）

4. **执行流程**
   ```
   工具调用 → needs_confirmation() →
     None → 直接执行
     str  → 检查 confirmed_paths →
       已确认 → 直接执行
       未确认 → 展示危险提示 → y → 加入缓存 + 执行 / n → 返回 "User denied"
   ```

**关键设计**（来自 `res/10. 安全性.pdf`）：
- 拒绝后应当继续循环，而不是终止 Agent，让模型提出替代方案
- 正则 + 词边界可以覆盖 95% 的危险命令识别
- 使用 `\b` 词边界确保 `rm` 不会误匹配 `perform` 中的字母

**产出文件**：
```
src/
└── permissions.py   # 权限确认系统
```

**阶段验收**：让 Agent 尝试 "删除 src/ 下所有空白文件"，系统应当提示确认 + 可以拒绝

---

## 体验阶段 — 流式输出 + 错误处理 + 会话

### Step 7：流式输出

**目标**：将 API 的流式响应实时输出给用户，提升交互体验，消除等待焦虑

**实施要点**：

1. **对接 API 流式模式**
   - 调用时传入 `stream=True`，返回一个可迭代的 chunk 流
   - 遍历 chunk，提取 `chunk.choices[0].delta.content` 和 `delta.tool_calls`

2. **增量文本输出**
   - 文本 delta 立即打印（`print(delta, end='', flush=True)`，不换行）
   - 工具调用中积累各 chunk 的 delta 直到 JSON 完整，再执行

3. **彩色 UI 输出** (`src/ui.py`)
   - 使用 `rich` 库（Python 生态最强终端 UI 库）
     - `rich.console.Console` 统一输出入口
     - `rich.spinner.Spinner` 展示工具执行中的 spinner
     - `rich.panel.Panel` 折叠展示超长工具结果
     - `rich.syntax.Syntax` 展示代码块时自动高亮
   - 颜色约定：用户输入蓝色、工具调用黄色、工具结果灰色、错误红色、费用统计暗色

**关键设计**（来自 `res/11. 用户体验.pdf`）：
- 流式输出可使感知延迟降低 5-30 倍，显著减少"是不是卡了"的焦虑感
- 工具调用过程中应展示 spinner，工具完成后立即展示结果，超过 500 字时折叠

**产出文件**：
```
src/
└── ui.py    # 终端 UI 输出工具集
```

---

### Step 8：错误重试 + 上下文压缩

**目标**：让 Agent 在面对 API 错误和超长对话时都能优雅降级

**实施要点**：

1. **指数退避重试** (`src/retry.py`)
   - 触发条件：限流（429）、服务器错误（500/502/503）、网络超时
   - 等待公式：`min(1 * 2**attempt, 30) + random.uniform(0, 1)` 秒
   - 最大重试 3 次
   - 配合 `threading.Event`，支持用户在等待期间按 Ctrl+C 中断

2. **上下文压缩** — Agent 层处理
   - 监测 API 返回的 `usage.prompt_tokens` 是否超过上下文窗口的 85%
   - 压缩策略：
     1. 保留系统提示（不压缩）
     2. 对中间的对话历史调用 LLM 自身生成摘要
     3. 重组为 `[摘要消息, "Understood.", 最后一条用户消息]`
   - 对话轮数 < 4 轮时不触发压缩

3. **手动压缩**
   - REPL 中输入 `/compact` 可主动触发压缩

**关键设计**（来自 `res/3. 上下文.pdf`）：
- 压缩阈值 85% 而非 95%，给工具结果留出足够空间
- 摘要内容应保留 "key decisions, file paths, and context"
- 压缩后必须保留至少一组 user-assistant 对话，否则 API 报错

**产出文件**：
```
src/
└── retry.py   # 重试逻辑
```

---

### Step 9：会话持久化 + REPL 命令扩展

**目标**：支持会话恢复，让用户可以从上次中断的地方继续工作

**实施要点**：

1. **会话持久化** (`src/session.py`)
   - 保存路径：`~/.harness/sessions/{id}.json`
   - 内容：消息历史 + 元数据，用内置 `json` 模块读写
   - `--resume` 参数（argparse）指定会话 ID 恢复

2. **REPL 命令扩展**
   - `/clear` — 清空当前对话历史
   - `/cost` — 显示本次会话 Token 用量和费用估算
   - `/compact` — 手动触发上下文压缩
   - `/help` — 展示所有可用命令

3. **Ctrl+C 双级处理**
   - 使用 `signal.signal(SIGINT, handler)` 捕获中断信号
   - Agent 运行中按 Ctrl+C → 置位 `stop_event`，中断当前任务，回到输入提示
   - Agent 空闲时按 Ctrl+C → 退出程序

4. **Token 用量展示**
   - 实时累计 input/output tokens（存入会话 dataclass）
   - 每轮对话后显示增量
   - `/cost` 命令显示总计

**关键设计**（来自 `res/11. 用户体验.pdf`、`res/12. 最小必要.pdf`）：
- 会话文件用 JSON 格式存取，前 64 个字符作为显示名称
- 正确处理 Ctrl+C 两级行为，是 Agent 体验的核心细节

**产出文件**：
```
src/
└── session.py   # 会话持久化
```

**阶段验收**：进行 50+ 轮对话后不崩溃，API 报 context limit 时自动压缩并继续运行

---

## 进阶阶段 — 记忆 + 扩展性

### Step 10：记忆系统

**目标**：让 Agent 具备跨会话记忆能力，积累项目知识和用户偏好

**实施要点**：

1. **记忆存储** (`src/memory.py`)
   - 存放路径：`~/.harness/memory/`
   - 索引文件：`MEMORY.md`，列出所有记忆条目的摘要和路径
   - 单条记忆：Markdown + YAML frontmatter 格式，用 `pathlib` 读写

2. **记忆分类**
   - `user`：用户偏好（如"用户喜欢简洁的注释风格"）
   - `feedback`：使用反馈（"用户不满意这种输出方式"）+ Why + 如何改进
   - `project`：项目决策（"2026-03-05 决定使用 SQLAlchemy"）+ 背景 + 结论
   - `reference`：参考文档和规范链接

3. **记忆触发**
   - `/remember` 命令主动记录
   - 对话结束后自动检测是否有值得记忆的内容

4. **记忆检索**
   - 每次启动时读取 `MEMORY.md` 索引，注入系统提示
   - 相关记忆按优先级排序后注入（不超过 2000 Token）

5. **团队共享**
   - 项目级记忆存放在项目根目录 `.harness/memory/`
   - 也可写入 CLAUDE.md（永久性约束）

**关键设计**（来自 `res/8. 记忆.pdf`）：
- 记忆本质是"让 Agent 记住用户上次告诉它的事情"，而不是 RAG
- MEMORY.md 作为记忆索引，避免每次全量扫描记忆目录
- feedback 类型的记忆价值最大，可显著减少重复错误

**产出文件**：
```
src/
└── memory.py   # 记忆系统
```

---

### Step 11：高级安全防护 + Hooks 扩展机制

**目标**：完善安全防线并提供可扩展的 Hook 机制

**实施要点**：

1. **Shell 命令安全加固**
   - 白名单放行：`grep`、`ls`、`cat`、`git log` 等只读命令无需确认
   - 过滤危险环境变量：`LD_PRELOAD`、`PYTHONPATH` 等注入向量（从 `subprocess` 的 `env` 参数中剔除）
   - 检测命令注入：管道、重定向、命令替换的组合

2. **敏感文件保护**
   - 拒绝写入：`.gitconfig`、`.bashrc`、`.zshrc`、`.env`、`.harness/` 等
   - 非 yolo 模式下强制确认以上文件的任何写操作

3. **实现 Hooks 机制** (`src/hooks.py`)
   - 定义两个 Hook 事件点：
     - `pre_tool_use`：工具执行前，可用于日志记录或拦截
     - `post_tool_use`：工具执行后，可用于通知或审计
   - Hook 配置文件：`.harness/hooks.json`
   - Hook 通过 `subprocess.run()` 执行外部脚本（可以是任意可执行文件）

4. **规则化权限**
   - `~/.harness/settings.json` 配置 allow/deny 规则
   - 支持 `ToolName(pattern)` 格式的路径匹配

**关键设计**（来自 `res/10. 安全性.pdf`、`res/6. Hooks 系统.pdf`）：
- 危险命令拦截覆盖约 60% 的真实破坏场景，其余靠"确认"兜底
- Hooks 与 Agent Loop 的关系类似于 AOP（面向切面编程），不侵入核心逻辑
- Hook 退出码约定：0 = 正常，1 = 警告（继续执行），2 = 阻断（终止工具调用）

**产出文件**：
```
src/
├── hooks.py        # Hooks 扩展机制
└── security.py     # 高级安全防护
```

**阶段验收**：Agent 执行任意代码库操作时，Hooks 日志正确记录每次工具调用，安全规则拦截敏感文件写入

---

## 最终目录结构

```
harness/
├── .ENV                          # API 密钥（不提交 git）
├── .gitignore
├── .cursor/
│   └── rules/                    # Cursor 项目规则
│       ├── project-overview.mdc  # 项目背景与计划概览
│       ├── task-protocol.mdc     # 任务追踪与日志协议
│       └── python-standards.mdc  # Python 编码规范
├── CLAUDE.md                     # 项目上下文（Agent 自身使用）
├── PLAN.md                       # 完整实施计划
├── PROGRESS.md                   # 进度追踪 + 子任务清单 + 变更日志
├── requirements.txt              # Python 依赖
├── res/                          # 参考文档（12 份 PDF）
├── dashboard/                    # Streamlit 教学仪表盘
│   ├── app.py                    # 仪表盘主入口
│   ├── pages/                    # 每个 Step 的交互页面
│   │   ├── step0_overview.py
│   │   ├── step1_api.py
│   │   ├── step2_prompt.py
│   │   ├── ...
│   │   └── step11_hooks.py
│   └── components/
│       └── shared.py             # 共享 UI 组件
└── src/                          # Agent 核心代码
    ├── main.py                   # 程序入口
    ├── cli.py                    # CLI 界面 + REPL
    ├── client.py                 # 千问 API 客户端
    ├── agent.py                  # Agent 主循环与对话管理
    ├── prompt.py                 # 提示词组装器
    ├── system_prompt.md          # 系统提示词模板
    ├── tools.py                  # 工具定义 + 执行器
    ├── permissions.py            # 权限确认系统
    ├── security.py               # 高级安全防护
    ├── retry.py                  # 重试逻辑
    ├── session.py                # 会话持久化
    ├── memory.py                 # 记忆系统
    ├── hooks.py                  # Hooks 扩展机制
    └── ui.py                     # 终端 UI 工具集
```

---

## 技术栈

| 类别 | 选型 | 说明 |
|------|------|------|
| 运行时 | Python 3.11+ | 生态丰富，内置模块减少外部依赖 |
| 模型 | 千问（qwen-plus/qwen-max） | 兼容 OpenAI 协议，直接用 openai SDK |
| SDK | `openai` pip 包 | 复用 OpenAI 格式直接对接千问 |
| 终端 UI | `rich` | Python 生态最强终端库，含 spinner/panel/syntax |
| 教学仪表盘 | `streamlit` | 轻量级 Web UI，每个 Step 配一个交互页面 |
| 交互输入 | 内置 `readline` + `input()` | 无需额外依赖，支持历史记录 |
| 文件操作 | 内置 `pathlib` | 路径操作，比 `os.path` 更现代 |
| Shell 执行 | 内置 `subprocess` | 执行外部命令，捕获输出 |
| 文件搜索 | 内置 `glob` / `pathlib.rglob` | 无需额外依赖 |
| 配置加载 | `python-dotenv` | 从 .ENV 读取 API 密钥 |
| 参数解析 | 内置 `argparse` | CLI 参数解析 |
| 信号处理 | 内置 `signal` | Ctrl+C 双级处理 |
| 版本管理 | Git + tag | 每个 Step 封版打 tag，可回溯 |

---

## 千问 API 接入说明

```python
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(".ENV")

client = OpenAI(
    api_key=os.environ.get("Ali_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

# 流式调用
stream = client.chat.completions.create(
    model="qwen-plus",
    messages=[...],
    tools=[...],        # function calling
    stream=True,        # 启用流式
)

for chunk in stream:
    delta = chunk.choices[0].delta
    if delta.content:
        print(delta.content, end="", flush=True)
    if delta.tool_calls:
        # 积累 tool call 分片，JSON 完整后执行
        ...
```

与 Claude API 的差异注意点：
- 工具使用 OpenAI 格式的 `tools` 字段，而非 Anthropic 格式
- Tool calling 响应字段是 `tool_calls`，而非 `tool_use`
- 工具结果角色是 `"tool"`，而非 `"tool_result"`
- 流式格式遵循标准 OpenAI SSE 格式

---

## 每步验收标准

| 步骤 | 验收方式 |
|------|---------|
| Step 0 | git 仓库初始化，`streamlit run dashboard/app.py` 可启动首页 |
| Step 1 | 终端输出 "你好" 的模型响应 |
| Step 2 | 系统提示包含当前目录和 git 状态信息 |
| Step 3 | 让 Agent 分析 requirements.txt，它能自主调用 read_file 工具 |
| Step 4 | 让 Agent 在某个文件中执行 search-and-replace，旧内容消失新内容正确出现 |
| Step 5 | 让 Agent 在整个 .py 文件中查找所有 TODO 注释，结果准确 |
| Step 6 | 让 Agent 执行 `rm` 操作，系统弹出确认提示且可以拒绝 |
| Step 7 | 模型输出逐字符实时流式打印到终端，工具调用时显示 spinner |
| Step 8 | 发送 30+ 轮超长对话后上下文自动压缩，对话不中断 |
| Step 9 | 退出后使用 `--resume` 恢复，上下文完整无误 |
| Step 10 | 输入 "记住我喜欢简洁注释"，下次启动后 Agent 记得这个偏好 |
| Step 11 | 让 Agent 使用 `ls` 命令（只读，放行）vs `rm` 命令（危险，拦截）对比行为 |

---

## 参考文档对照

| 步骤 | 参考文件 | 核心内容 |
|------|---------|-----------|
| Step 0 | `PLAN.md` + 所有 `res/*.pdf` | 整体计划梳理与项目基础设施 |
| Step 1 | `res/1. 首页.pdf` | 整体架构与千问接入方式 |
| Step 2 | `res/3. 上下文.pdf` | 提示词结构、CLAUDE.md 加载机制 |
| Step 3 | `res/2. 代理循环.pdf` | Agent Loop 实现细节 |
| Step 4 | `res/5. 代码编辑.pdf` | search-and-replace 策略与唯一性约束 |
| Step 5 | `res/4. 工具.pdf` | 工具设计原则与文件搜索实现 |
| Step 6 | `res/10. 安全性.pdf` | 权限系统与危险命令识别 |
| Step 7 | `res/11. 用户体验.pdf` | 流式输出与 Spinner 状态机 |
| Step 8 | `res/3. 上下文.pdf` | 4 级压缩管道与 Token 预算管理 |
| Step 9 | `res/12. 最小必要.pdf` | CLI 最小必要组件与会话持久化 |
| Step 10 | `res/8. 记忆.pdf` | 4 类记忆系统与异步预加载 |
| Step 11 | `res/6. Hooks 系统.pdf` | Hook 类型、事件点与退出码约定 |

---

## 核心设计原则（贯穿始终）

1. **工具调用可观察** — 每次工具调用都应打印给用户看，不能在暗中执行
2. **危险操作可拒绝** — 任何破坏性操作都要经过用户确认，且拒绝后 Agent 继续运行
3. **上下文可压缩** — 对话超长时自动摘要，不因 context limit 崩溃
4. **费用可感知** — 每轮展示 token 消耗，让用户清楚成本
5. **状态可恢复** — 会话可持久化，从 git 历史和 CLAUDE.md 重建上下文
6. **行为可扩展** — 通过 Hooks 机制允许外部脚本介入 Agent 的每个操作节点

---

> 当前处于 **Step 0（准备阶段）**，子任务 0.1 已完成。
> 准备好继续 **Step 0.2（项目骨架搭建）** 时告诉我。
