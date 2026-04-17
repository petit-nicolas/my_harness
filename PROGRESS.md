# Harness 项目进度追踪

## 当前状态

- **当前阶段**：能力阶段
- **当前步骤**：Step 9 — 会话持久化 + REPL 命令扩展
- **当前子任务**：9.1 会话持久化（待开始）
- **最后更新**：2026-04-16

---

## 步骤进度

### Step 0：项目准备工作

- [x] 0.1 Cursor 规则与日志机制 — `.cursor/rules/` + `PROGRESS.md`
- [x] 0.2 项目骨架搭建 — git init、`.gitignore`、`requirements.txt`、目录结构
- [x] 0.3 Streamlit 仪表盘骨架 — `dashboard/app.py` + 首页

**封版标记**：已封版 (tag: step-0)

---

### Step 1：项目初始化 + 千问 API 对接

- [x] 1.1 API 客户端封装 — `src/client.py`，OpenAI SDK 对接千问
- [x] 1.2 连通性验证 — 发送 "你好"，终端打印模型回复
- [x] 1.3 Tool Calling 验证 — 定义假工具，验证模型返回 tool_calls
- [x] 1.4 仪表盘页面 — `dashboard/pages/step1_api.py`，可视化 API 调用过程

**封版标记**：已封版 (tag: step-1)

---

### Step 2：提示词编排系统

- [x] 2.1 系统提示词模板 — `src/system_prompt.md`，角色定义 + 占位符
- [x] 2.2 提示词组装器 — `src/prompt.py`，环境检测 + 动态注入
- [x] 2.3 CLAUDE.md 加载 — 递归查找 + 注入消息列表
- [x] 2.4 仪表盘页面 — 展示组装后的完整提示词，可编辑占位符

**封版标记**：已封版 (tag: step-2)

---

### Step 3：Agent 循环核心 + 基础 CLI

- [x] 3.1 工具注册表 — `src/tools.py`，JSON Schema 定义 + 工具字典
- [x] 3.2 基础工具实现 — read_file、write_file、run_shell 三个工具
- [x] 3.3 Agent 主循环 — `src/agent.py`，while True + tool_calls 处理
- [x] 3.4 CLI 界面 — `src/cli.py`，REPL + argparse
- [x] 3.5 仪表盘页面 — 展示 Agent 循环流程图 + 实时对话演示

**封版标记**：已封版 (tag: step-3)

---

### Step 4：Search-and-Replace 精准编辑工具

- [x] 4.1 edit_file 工具 — 唯一性校验 + 替换逻辑
- [x] 4.2 缩进保留 + 提示词更新 — 自动对齐 + 系统提示引导
- [x] 4.3 仪表盘页面 — 编辑效果 diff 对比展示

**封版标记**：已封版 (tag: step-4)

---

### Step 5：文件搜索与导航工具

- [x] 5.1 grep_search 工具 — rg 优先 + Python re 双路回退
- [x] 5.2 list_files 工具 — pathlib.glob + 黑名单过滤
- [x] 5.3 系统提示词更新 — 搜索工具使用规范
- [x] 5.4 仪表盘页面 — 搜索结果可视化 + 典型工作流演示

**封版标记**：已封版 (tag: step-5)

---

### Step 6：安全确认机制 + 危险命令拦截

- [x] 6.1 危险命令识别 — `src/permissions.py`，正则匹配（10 条规则）
- [x] 6.2 交互式确认 — confirm_fn 回调 + PermissionCache 授权缓存
- [x] 6.3 --yolo 模式 — argparse 参数，confirm_fn=None 跳过检查
- [x] 6.4 仪表盘页面 — 实时检测 + 规则列表 + yolo 说明

**封版标记**：已封版 (tag: step-6)

---

### Step 7：流式输出

- [x] 7.1 流式 API 对接 — `_collect_stream()` 文本 + tool_calls delta 累加
- [x] 7.2 增量文本输出 — `on_text_chunk` 回调，`stream=True` 默认启用
- [x] 7.3 Rich UI 集成 — `src/ui.py`，`StreamPrinter` + `thinking_spinner`
- [x] 7.4 仪表盘页面 — 流式对话体验 + chunk 累加原理 + 流式 vs 非流式对比

**封版标记**：已封版 (tag: step-7)

---

### Step 8：错误重试 + 上下文压缩

- [x] 8.1 指数退避重试 — `src/retry.py`，429/5xx/网络超时，client.py 集成
- [x] 8.2 上下文压缩策略 — 80% 阈值 + LLM 摘要 + 消息重组 + 自动触发
- [x] 8.3 /compact 命令 — REPL 集成，estimate_tokens 预览 + 手动触发
- [x] 8.4 仪表盘页面 — 退避策略模拟 + 压缩前后对比 + 代码原理
- [x] 8.5 Lazy Expansion 分层缓冲 — 大工具结果预览+缓存，read_tool_result 按需取后续

**封版标记**：已封版 (tag: step-8)

---

### Step 9：会话持久化 + REPL 命令扩展

- [x] 9.1 会话持久化 — `src/session.py`，JSON 存取 + save/load/list/delete + 自动清理
- [x] 9.2 REPL 命令扩展 — /save、/sessions、/load <id>、--resume、--sessions 参数
- [x] 9.3 Ctrl+C 双级处理 + Token 展示优化 — 退出自动保存 + /cost 增量展示
- [x] 9.4 仪表盘页面 — step9_session.py，历史浏览+JSON格式+命令速查+代码原理

**封版标记**：已封版 (tag: step-9)

---

### Step 10：记忆系统

- [x] 10.1 记忆存储与索引 — `src/memory.py`，MemoryEntry + MEMORY.md 四分类文件读写
- [x] 10.2 记忆分类与检索 — user/feedback/project/reference 四类 + 关键词搜索
- [x] 10.3 /remember /memories /forget /extract 命令 — 主动记录 + LLM 对话提取
- [x] 10.4 记忆注入 system prompt — {{memories}} 占位符 + prompt.py load_memories_context
- [x] 10.5 仪表盘页面 — step10_memory.py，记忆库管理+分类说明+Prompt注入演示+代码原理

**封版标记**：已封版 (tag: step-10)

---

### Step 11：高级安全防护 + Hooks 扩展机制

- [x] 11.1 Shell 安全加固 — `src/security.py`，settings.json 白/黑名单 + glob 匹配 + 可信路径
- [x] 11.2 Hooks 机制 — `src/hooks.py`，HookRegistry + pre/post 装饰器 + audit.log 内置钩子
- [x] 11.3 规则化权限集成 — agent.py 三层架构（Hooks → Policy → permissions），/stats 命令
- [x] 11.4 仪表盘页面 — step11_hooks.py，Hooks 演示+settings 编辑器+三层架构+审计日志

**封版标记**：已封版 (tag: step-11)

---

## 变更日志

| 日期 | 子任务 | 状态 | 备注 |
|------|--------|------|------|
| 2026-04-17 | 11.1-11.4 高级安全+Hooks 全套 | 完成 | hooks.py (HookRegistry+内置审计钩子)+security.py (settings.json Policy三层架构)+agent.py 集成+/stats 命令+仪表盘，Step 11 封版 |
| 2026-04-17 | 10.1-10.5 记忆系统全套 | 完成 | memory.py (MemoryEntry+MEMORY.md四分类)+/remember /memories /forget /extract命令+LLM自动提取+{{memories}}注入prompt+仪表盘，Step 10 封版 |
| 2026-04-17 | 9.1-9.4 会话持久化全套 | 完成 | session.py (JSON 存取+ID生成+自动清理)+CLI /save /sessions /load --resume --sessions+自动保存+仪表盘 step9_session.py，Step 9 封版 |
| 2026-04-16 | 8.5 Lazy Expansion 分层缓冲 | 完成 | _LAST_RESULTS 模块缓存+read_tool_result 工具+_truncate_for_history，8 项单元测试通过，step-8 tag 重打 |
| 2026-04-16 | 8.1-8.4 重试+压缩全套 | 完成 | retry.py+client集成+compact_context+/compact命令+仪表盘，Step 8 封版 |
| 2026-04-16 | 7.1-7.4 流式输出全套 | 完成 | _collect_stream+StreamPrinter+on_text_chunk+cli改造+仪表盘，Step 7 封版 |
| 2026-04-16 | 6.1-6.4 安全确认机制全套 | 完成 | permissions.py+confirm_fn+yolo+仪表盘，Step 6 封版 |
| 2026-04-16 | 5.1-5.4 搜索工具全套 | 完成 | grep_search(rg/re双路)+list_files(黑名单过滤)+提示词+仪表盘，Step 5 封版 |
| 2026-04-16 | 4.3 仪表盘页面 | 完成 | step4_edit.py，三 Tab：交互式体验+缩进对齐演示+edit vs write 对比，Step 4 封版 |
| 2026-04-16 | 4.2 缩进保留+提示词更新 | 完成 | system_prompt.md 补充 edit_file 三种失败场景处理指引 |
| 2026-04-16 | 4.1 edit_file 工具 | 完成 | 唯一性校验+缩进对齐+4项测试全通过 |
| 2026-04-16 | 3.5 仪表盘页面 | 完成 | step3_agent.py，实时对话+工具调用展示+消息历史，Step 3 封版 |
| 2026-04-16 | 3.4 CLI 界面 | 完成 | src/cli.py，REPL+--prompt 模式，Ctrl+C 双级，rich 彩色输出，全链路验证通过 |
| 2026-04-16 | 3.3 Agent 主循环 | 完成 | AgentSession + run_agent()，工具调用闭环验证通过，Token 追踪正常 |
| 2026-04-16 | 3.1-3.2 工具注册表+三工具实现 | 完成 | src/tools.py，run_tool() 分发，5项测试全通过 |
| 2026-04-16 | 2.4 仪表盘页面 | 完成 | step2_prompt.py，三 Tab：模板/组装结果/组件拆解，Step 2 封版 |
| 2026-04-16 | 2.1-2.3 提示词模板+组装器+CLAUDE.md | 完成 | system_prompt.md 占位符，prompt.py 三函数，组装后 1302 字符验证通过 |
| 2026-04-16 | 1.4 仪表盘页面 | 完成 | step1_api.py，两个 Tab：连通性测试 + Tool Calling 演示，Step 1 封版 |
| 2026-04-16 | 1.3 Tool Calling 验证 | 完成 | tool_calls 结构正确，工具结果回传后对话继续，两项断言通过 |
| 2026-04-16 | 1.2 连通性验证 | 完成 | 基础对话 2.68s，流式输出正常，两项测试全部通过 |
| 2026-04-16 | 1.1 API 客户端封装 | 完成 | src/client.py，单例模式，chat() 统一接口，key 加载验证通过 |
| 2026-04-16 | 0.3 Streamlit 仪表盘骨架 | 完成 | dashboard/app.py + step0_overview.py，HTTP 200 验证通过，Step 0 封版 |
| 2026-04-16 | 0.2 项目骨架搭建 | 完成 | git init、.gitignore、requirements.txt、src/ + dashboard/ 目录、依赖安装验证、初始 commit |
| 2026-04-15 | 0.1 Cursor 规则与日志机制 | 完成 | 创建 3 份 .cursor/rules/ 规则 + PROGRESS.md |
