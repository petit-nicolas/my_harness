# 物理教学 Agent (Physics Tutor) 进度追踪

## 当前状态

- **分支**：`vertical-industry`
- **当前阶段**：Phase 0 — 治理基础设施
- **当前步骤**：Phase 0 完成，等待 V1 开启
- **最后更新**：2026-04-15

---

## 整体规划概览

| 阶段 | 目标 | 封版 tag |
|------|------|----------|
| **Phase 0** | 治理基础设施（规则 / 计划 / 日志 / 骨架） | `phy-v0` |
| **V1** | Wiki 基础设施（schema + 四工具 + 浏览页） | `phy-v1` |
| **V2** | Ingest 流水线 + Lint + 教材骨架 | `phy-v2` |
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

### V1：Wiki 基础设施

- [ ] V1.1 编写 `res/phy/schemas/PHYSICS_SCHEMA.md`（frontmatter 字段、双向链接语法、log 格式）
- [ ] V1.2 建立 `res/phy/wiki/index.md` 与 `log.md` 骨架
- [ ] V1.3 实现 `src/phy/wiki.py` — `wiki_read` / `wiki_write` / `wiki_search` / `wiki_index` 四工具
- [ ] V1.4 工具注册到物理模式，写冒烟测试脚本
- [ ] V1.5 仪表盘 `dashboard/pages/phy_1_wiki.py`（页面浏览 + 反向索引视图）

**封版标记**：未开始（目标 tag: phy-v1）

---

### V2：Ingest 流水线 + Lint

- [ ] V2.1 依赖安装 `pypdf` / `markdownify`，建立 raw/ 预置人教版目录骨架
- [ ] V2.2 实现 `src/phy/ingest.py` 的 `ingest_source` 工具（PDF/MD/HTML → 抽概念 → 多页更新 + 追加 log）
- [ ] V2.3 实现 `wiki_lint`（孤儿页 / 公式冲突 / 缺失引用 / frontmatter 校验）
- [ ] V2.4 端到端测试：吸收一个章节并通过 lint
- [ ] V2.5 仪表盘扩展 ingest 视图（源 → 命中页面 → log 追加）

**封版标记**：未开始（目标 tag: phy-v2）

---

### V3：教师 Persona + 教学策略

- [ ] V3.1 编写 `src/phy/physics_prompt.md`（顶级教师人格 + 苏格拉底守则 + wiki 使用规范）
- [ ] V3.2 扩展 `src/prompt.py` 支持 `--mode physics` 分支（最小化侵入主线）
- [ ] V3.3 实现 `src/phy/strategies.py` 三个策略工具（`teach_analogy` / `teach_derivation` / `teach_misconception`）
- [ ] V3.4 CLI `harness --mode physics` 端到端跑通
- [ ] V3.5 仪表盘新增教学策略试触发演示

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

### V6：自适应练习题

- [ ] V6.1 `quiz_generate`（从 wiki 抽取 + 基于 student 弱点定向）
- [ ] V6.2 `quiz_evaluate`（判分 + 错因分析 + 回写 StudentMap）
- [ ] V6.3 错题本：双向链接到 wiki 节点与 student 节点
- [ ] V6.4 IRT-lite 难度调节（正确率窗口 → 动态难度）
- [ ] V6.5 仪表盘集成：一键"做题" + 即时反馈

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
| 2026-04-15 | P0.1-P0.6 Phase 0 全部完成 | 完成 | 建立 `physics-project.mdc` + `PHY_PLAN.md` + `PHY_PROGRESS.md` + 目录骨架，打 tag phy-v0 |

---

## 子任务推进原则（对齐 task-protocol.mdc）

- 每次对话启动先读本文件确认进度
- 使用 `VN.M` 编号推进，**不跨 step 工作**
- 每完成一个子任务勾选 + 追加变更日志（最新在最上）
- 完成 `VN` 全部子任务后 commit + `git tag phy-vN` + 标记封版
- 遇到和权威资料冲突时按 `.cursor/rules/physics-project.mdc` 的错误处理流程回写
