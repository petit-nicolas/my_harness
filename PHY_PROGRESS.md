# 物理教学 Agent (Physics Tutor) 进度追踪

## 当前状态

- **分支**：`vertical-industry`
- **当前阶段**：V1 — Wiki 基础设施 + MinerU 解析底座（规划已优化，等待启动 V1.1）
- **当前步骤**：phy-v0 已封版；2026-04-19 完成 V1/V2 规划优化（MinerU + Reviewer + 8 步 ingest）；2026-04-19 完成 Builder/Runner 二分 + Wiki Feedback Loop 设计
- **最后更新**：2026-04-19

---

## 整体规划概览

| 阶段 | 目标 | 封版 tag |
|------|------|----------|
| **Phase 0** | 治理基础设施（规则 / 计划 / 日志 / 骨架） | `phy-v0` |
| **V1** | Wiki 基础设施 + MinerU 解析底座（schema + 四工具 + MinerU + 浏览页） | `phy-v1` |
| **V2** | Ingest 8 步流水线 + Reviewer Persona + Lint + 端到端实跑首章 | `phy-v2` |
| **V3** | 教师 Persona + 教学策略库 | `phy-v3` |
| **V4** | Student Map + 自动评估 hook | `phy-v4` |
| **V5** | HTML5 交互演示 + Plotly 场/函数 | `phy-v5` |
| **V6** | 自适应练习题系统 + 错题本 | `phy-v6` |
| **V7** | 学习报告 + 仪表盘收束 | `phy-v7` |

详细目标、架构与技术选型见 `PHY_PLAN.md`。

---

## 步骤进度

### Phase 0：治理基础设施

- [x] P0.1 切换 `vertical-industry` 分支，确认工作区状态
- [x] P0.2 新增 `.cursor/rules/physics-project.mdc`，更新 `task-protocol.mdc`
- [x] P0.3 编写 `PHY_PLAN.md`（V1-V7 完整目标 + 架构图 + 技术选型）
- [x] P0.4 编写 `PHY_PROGRESS.md`（本文件）
- [x] P0.5 建立 `res/phy/{wiki,raw,schemas,demo_templates}/`、`src/phy/` 骨架 + README；更新项目根 `README.md`
- [x] P0.6 提交并打 tag `phy-v0`，推送 `vertical-industry` 分支

**封版标记**：待提交后标记为 已封版 (tag: phy-v0)

---

### V1：Wiki 基础设施 + MinerU 解析底座

- [ ] V1.1 编写 `res/phy/schemas/PHYSICS_SCHEMA.md`（frontmatter 必填 `images` / `formulas` 字段 + 双向链接 + 8 步 ingest 的 log 格式约定）
- [ ] V1.2 建立 `res/phy/wiki/{index.md, log.md, overview.md}` 骨架（含双索引模板与状态机条目示例）
- [ ] V1.3 移植并物理特化 `src/phy/tools/mineru.py`（默认 vlm + 强制 `--page-ranges` + 自动迁移图片到 `<source-stem>-images/` + 自动重写 markdown 图片路径），更新 `requirements.txt` 加入 `requests`
- [ ] V1.4 新增 `.cursor/rules/mineru-tool.mdc` 已完成（V0 阶段顺手做掉，V1 阶段验证此规则被遵循）；新增 `.ENV.example` 模板
- [ ] V1.5 实现 `src/phy/wiki.py` — `wiki_read` / `wiki_write` / `wiki_search` / `wiki_index` 四工具，**注册时按 mode 分级**（read/search 为 builder+runner，write/index 仅 builder）
- [ ] V1.6 冒烟测试脚本 `tests/phy/test_v1_smoke.py`：mineru 解析一个小 PDF + 创建一个测试 wiki 页 + 索引自动更新 + 图片正确落盘
- [ ] V1.7 仪表盘 `dashboard/pages/phy_1_wiki.py`（页面浏览 + 反向链接 + log 状态机三栏视图：active/paused/done）

**封版标记**：未开始（目标 tag: phy-v1）

---

### V2：Ingest 8 步流水线 + Reviewer Persona + Lint + 端到端实跑

- [ ] V2.1 编写 `src/phy/reviewers/physics_teacher_reviewer.md`（资深教研组长人格 + `ingest.split_review` 输入输出契约）
- [ ] V2.2 实现 `src/phy/reviewers/__init__.py` 通用 `call_reviewer(persona_id, payload)`：独立 LLM session、低 temperature、JSON 解析、写 audit log、confidence 阈值标记
- [ ] V2.3 实现 `src/phy/ingest.py` 的 8 步状态机（`init_log` / `mineru_parse` / `read_content` / `split_review` / `create_source_summary` / `create_concept_pages` / `update_index` / `lint_check`），每步独立可恢复
- [ ] V2.4 启动协议：`ingest_chapter` 工具调用前先扫 `wiki/log.md`，发现 `state: active|paused` 优先恢复（不允许并发）
- [ ] V2.5 实现 `wiki_lint`（孤儿页 / 缺图引用 / 公式冲突 / frontmatter 缺字段 / wikilink 断裂），可作为独立工具或 ingest 第 8 步
- [ ] V2.6 用户提供首章教材 → 由 Agent 自行选定 ingest 范围 → 端到端实跑 → 中途模拟一次中断 → 重启从 log 断点续跑 → 最终 lint 全绿
- [ ] V2.7 仪表盘扩展 `phy_1_wiki.py` 的 ingest 视图（源 → 8 步进度条 → reviewer 决策展示 + 真人覆写按钮 → 命中页面）

**封版标记**：未开始（目标 tag: phy-v2）

---

### V3：教师 Persona + 教学策略 + Feedback Loop 接入

- [ ] V3.1 编写 `src/phy/physics_prompt.md`（顶级教师人格 + 苏格拉底守则 + wiki 使用规范 + feedback_submit 触发指南）
- [ ] V3.2 扩展 `src/prompt.py` 支持 `--mode physics` 分支（最小化侵入主线），引入 builder/runner 工具表过滤
- [ ] V3.3 实现 `src/phy/strategies.py` 三个策略工具（`teach_analogy` / `teach_derivation` / `teach_misconception`，runner 限定）
- [ ] V3.4 实现 `src/phy/feedback.py`：runner 端 `feedback_submit`（仅 `O_CREAT | O_EXCL` 写 inbox）+ builder 端 `feedback_resolve` / `feedback_reject` + 去重检查
- [ ] V3.5 编写 `src/phy/reviewers/feedback_reviewer.md`（cursor 充当，输出 accept/reject/needs_more_info + reasoning）
- [ ] V3.6 建立 `res/phy/wiki/feedback/{inbox,processed,rejected}/` 目录骨架 + README；`src.security` 加 file policy 锁死写权限
- [ ] V3.7 教学结束 hook：post-session 扫对话决定是否 submit；Cursor build session 启动协议：扫 inbox 报告未处理数量
- [ ] V3.8 端到端验证：CLI `harness --mode physics` 启动；模拟"老师讲错了"触发 feedback_submit；模拟一个 ticket 由 Cursor + feedback_reviewer 走完 accept 流程并修订 wiki
- [ ] V3.9 仪表盘新增 Feedback 视图（inbox/processed/rejected 三栏 + ticket 详情 + 教学策略试触发演示）

**封版标记**：未开始（目标 tag: phy-v3）

---

### V4：学生知识图谱

- [ ] V4.1 `StudentMap` 数据结构与磁盘存储（`res/phy/students/<id>.json`，`.gitignore` 排除）
- [ ] V4.2 工具 `student_get` / `student_update` / `student_assess`
- [ ] V4.3 `post_tool_use` hook：对话后自动评估并更新掌握度
- [ ] V4.4 节点 id 与 wiki 对齐校验（引用不存在的知识点报错）
- [ ] V4.5 仪表盘 `phy_2_student_map.py`（pyvis 交互图 + 掌握度热度）

**封版标记**：未开始（目标 tag: phy-v4）

---

### V5：HTML5 交互演示

- [ ] V5.1 建立 `res/phy/demo_templates/` 目录，统一模板接口（参数 JSON → 填充位）
- [ ] V5.2 实现 6 个核心模板：斜抛 / 单摆 / 弹簧振子 / 简单电路 / 机械波 / 天体运动
- [ ] V5.3 实现 `src/phy/render.py` 的 `render_demo` / `render_plot` 工具
- [ ] V5.4 沙箱与安全：iframe sandbox、参数白名单校验
- [ ] V5.5 仪表盘 `phy_3_tutor.py`（对话 + iframe demo 联动）

**封版标记**：未开始（目标 tag: phy-v5）

---

### V6：自适应练习题 + 数据信号触发反馈

- [ ] V6.1 `quiz_generate`（从 wiki 抽取 + 基于 student 弱点定向）
- [ ] V6.2 `quiz_evaluate`（判分 + 错因分析 + 回写 StudentMap）
- [ ] V6.3 错题本：双向链接到 wiki 节点与 student 节点
- [ ] V6.4 IRT-lite 难度调节（正确率窗口 → 动态难度）
- [ ] V6.5 `post_tool_use` hook：监测 quiz_evaluate 信号（同 wiki 节点 N 名学生连错率 > 阈值 / IRT 难度估计偏离 wiki level）→ 自动 `feedback_submit`，去重 24h
- [ ] V6.6 仪表盘集成：一键"做题" + 即时反馈 + 自动 submit 信号面板

**封版标记**：未开始（目标 tag: phy-v6）

---

### V7：学习报告 + 仪表盘收束

- [ ] V7.1 报告数据聚合（周/月掌握度变化、错题 top、复习推荐）
- [ ] V7.2 `phy_4_report.py` 报告视图
- [ ] V7.3 学生/教师视图切换
- [ ] V7.4 一键导出学习档案（JSON + Markdown）
- [ ] V7.5 端到端教学场景串讲（录屏或脚本）

**封版标记**：未开始（目标 tag: phy-v7）

---

## 变更日志

| 日期 | 子任务 | 状态 | 备注 |
|------|--------|------|------|
| 2026-04-19 | Builder/Runner 二分 + Feedback Loop 设计 | 完成 | 明确 Cursor 做 Build-time wiki 维护、Harness 做 Runtime 教学；工具按 mode 分级；新增 Wiki Feedback Loop（runner append-only inbox/，cursor 审核处理）；Reviewer 表加 executor 字段（V2 V3 走 cursor，V4 V6 V7 走 harness）；V3 加 feedback 接入 4 个子任务，V6 加自动信号触发 |
| 2026-04-19 | V1/V2 规划优化 | 完成 | 引入 MinerU + Reviewer Persona + 8 步 ingest 状态机 + sources/ 摘要层 + 图片资产保留；新增 `mineru-tool.mdc`；扩展 `physics-project.mdc` |
| 2026-04-15 | P0.1-P0.6 Phase 0 全部完成 | 完成 | 建立 `physics-project.mdc` + `PHY_PLAN.md` + `PHY_PROGRESS.md` + 目录骨架，打 tag phy-v0 |

---

## 子任务推进原则（对齐 task-protocol.mdc）

- 每次对话启动先读本文件确认进度
- 使用 `VN.M` 编号推进，**不跨 step 工作**
- 每完成一个子任务勾选 + 追加变更日志（最新在最上）
- 完成 `VN` 全部子任务后 commit + `git tag phy-vN` + 标记封版
- 遇到和权威资料冲突时按 `.cursor/rules/physics-project.mdc` 的错误处理流程回写
