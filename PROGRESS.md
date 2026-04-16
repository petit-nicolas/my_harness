# Harness 项目进度追踪

## 当前状态

- **当前阶段**：骨架阶段
- **当前步骤**：Step 1 — 项目初始化 + 千问 API 对接
- **当前子任务**：1.2 连通性验证（待开始）
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
- [ ] 1.2 连通性验证 — 发送 "你好"，终端打印模型回复
- [ ] 1.3 Tool Calling 验证 — 定义假工具，验证模型返回 tool_calls
- [ ] 1.4 仪表盘页面 — `dashboard/pages/step1_api.py`，可视化 API 调用过程

**封版标记**：未封版

---

### Step 2：提示词编排系统

- [ ] 2.1 系统提示词模板 — `src/system_prompt.md`，角色定义 + 占位符
- [ ] 2.2 提示词组装器 — `src/prompt.py`，环境检测 + 动态注入
- [ ] 2.3 CLAUDE.md 加载 — 递归查找 + 注入消息列表
- [ ] 2.4 仪表盘页面 — 展示组装后的完整提示词，可编辑占位符

**封版标记**：未封版

---

### Step 3：Agent 循环核心 + 基础 CLI

- [ ] 3.1 工具注册表 — `src/tools.py`，JSON Schema 定义 + 工具字典
- [ ] 3.2 基础工具实现 — read_file、write_file、run_shell 三个工具
- [ ] 3.3 Agent 主循环 — `src/agent.py`，while True + tool_calls 处理
- [ ] 3.4 CLI 界面 — `src/cli.py`，REPL + argparse
- [ ] 3.5 仪表盘页面 — 展示 Agent 循环流程图 + 实时对话演示

**封版标记**：未封版

---

### Step 4：Search-and-Replace 精准编辑工具

- [ ] 4.1 edit_file 工具 — 唯一性校验 + 替换逻辑
- [ ] 4.2 缩进保留 + 提示词更新 — 自动对齐 + 系统提示引导
- [ ] 4.3 仪表盘页面 — 编辑效果 diff 对比展示

**封版标记**：未封版

---

### Step 5：文件搜索与导航工具

- [ ] 5.1 grep_search 工具 — subprocess 调用 grep/rg
- [ ] 5.2 list_files 工具 — pathlib.rglob + 排除规则
- [ ] 5.3 仪表盘页面 — 搜索结果可视化

**封版标记**：未封版

---

### Step 6：安全确认机制 + 危险命令拦截

- [ ] 6.1 危险命令识别 — `src/permissions.py`，正则匹配
- [ ] 6.2 交互式确认 — y/n 提示 + 路径缓存
- [ ] 6.3 --yolo 模式 — argparse 参数 + 跳过逻辑
- [ ] 6.4 仪表盘页面 — 安全规则配置界面 + 拦截演示

**封版标记**：未封版

---

### Step 7：流式输出

- [ ] 7.1 流式 API 对接 — stream=True + chunk 遍历
- [ ] 7.2 增量文本输出 — 逐字打印 + tool_calls 积累
- [ ] 7.3 Rich UI 集成 — `src/ui.py`，彩色输出 + spinner
- [ ] 7.4 仪表盘页面 — 流式效果演示

**封版标记**：未封版

---

### Step 8：错误重试 + 上下文压缩

- [ ] 8.1 指数退避重试 — `src/retry.py`，429/5xx/超时处理
- [ ] 8.2 上下文压缩策略 — 85% 阈值 + LLM 摘要 + 消息重组
- [ ] 8.3 /compact 命令 — REPL 集成 + 手动触发

**封版标记**：未封版

---

### Step 9：会话持久化 + REPL 命令扩展

- [ ] 9.1 会话持久化 — `src/session.py`，JSON 存取 + --resume
- [ ] 9.2 REPL 命令扩展 — /clear、/cost、/help
- [ ] 9.3 Ctrl+C 双级处理 + Token 展示 — signal 捕获 + 费用统计

**封版标记**：已封版 (tag: step-0)

---

### Step 10：记忆系统

- [ ] 10.1 记忆存储与索引 — `src/memory.py`，MEMORY.md 索引机制
- [ ] 10.2 记忆分类与检索 — user/feedback/project/reference 四类
- [ ] 10.3 /remember 命令 + 自动记忆 — 主动记录 + 对话后提取

**封版标记**：已封版 (tag: step-0)

---

### Step 11：高级安全防护 + Hooks 扩展机制

- [ ] 11.1 Shell 安全加固 + 敏感文件保护 — `src/security.py`
- [ ] 11.2 Hooks 机制 — `src/hooks.py`，pre/post_tool_use
- [ ] 11.3 规则化权限 — settings.json + 路径匹配

**封版标记**：未封版

---

## 变更日志

| 日期 | 子任务 | 状态 | 备注 |
|------|--------|------|------|
| 2026-04-16 | 1.1 API 客户端封装 | 完成 | src/client.py，单例模式，chat() 统一接口，key 加载验证通过 |
| 2026-04-16 | 0.3 Streamlit 仪表盘骨架 | 完成 | dashboard/app.py + step0_overview.py，HTTP 200 验证通过，Step 0 封版 |
| 2026-04-16 | 0.2 项目骨架搭建 | 完成 | git init、.gitignore、requirements.txt、src/ + dashboard/ 目录、依赖安装验证、初始 commit |
| 2026-04-15 | 0.1 Cursor 规则与日志机制 | 完成 | 创建 3 份 .cursor/rules/ 规则 + PROGRESS.md |
