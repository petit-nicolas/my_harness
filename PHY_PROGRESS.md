# 物理教学 Agent (Physics Tutor) 进度追踪

## 当前状态

- **分支**：`vertical-industry`
- **当前阶段**：V1 — Wiki 基础设施 + MinerU 解析底座（**全部子任务完成 ✅，待封版 phy-v1**）
- **当前步骤**：V1.7 完成 ✅；V1 可封版，打 tag `phy-v1` 后进入 V2
- **最后更新**：2026-04-20

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

- [x] V1.1 编写 `res/phy/schemas/PHYSICS_SCHEMA.md`（frontmatter 必填 `images` / `formulas` 字段 + 双向链接 + 8 步 ingest 的 log 格式约定）
- [x] V1.2 建立 `res/phy/wiki/{index.md, log.md, overview.md}` 骨架（含双索引模板与三类 log 条目示例）
- [x] V1.3 移植并物理特化 `src/phy/tools/mineru.py`（默认 vlm + 强制 `--page-ranges` + 自动迁移图片到 `<source-stem>-images/` + 自动重写 markdown 图片路径），更新 `requirements.txt` 加入 `requests`
- [x] V1.4 验证 `mineru-tool.mdc` 被实现严格遵守（16 条规则全 ✅，含新增 30 页软上限警告）；完善 `.ENV.example`（REPLACE_ME 占位符 + 双侧自检命令）
- [x] V1.5 实现 `src/phy/wiki.py` — `wiki_read` / `wiki_write` / `wiki_search` / `wiki_index` 四工具，**注册时按 mode 分级**（read/search 为 builder+runner，write/index 仅 builder）
- [x] V1.6 冒烟测试脚本 `tests/phy/test_v1_smoke.py`：mineru 纯函数 + wiki 端到端流水线（write→read→search→index→rebuild→二次幂等）+ mode 隔离（**runner 严格只读**）+ 断裂链接识别 + 图片路径双前缀回归
- [x] V1.7 仪表盘 `dashboard/pages/phy_1_wiki.py`（4 Tab：总览 / 页面浏览 / log 状态机三栏 / Feedback Inbox；**严格只读**）

**封版标记**：待封版（目标 tag: phy-v1，V1.1-V1.7 全部完成）

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
| 2026-04-20 | V1.7 仪表盘 phy_1_wiki.py | 完成 | 实现 `dashboard/pages/phy_1_wiki.py`（约 410 行，零 lint）。**4 个 Tab 布局**：(1) **总览** — 4 个 metric 卡片（概念页/摘要页/反向链接/断裂链接，断裂链接以 `-N 待修` 红色 delta 呈现）+ 学科/level 双列分布 + 断裂链接 expander；(2) **页面浏览** — 左侧 selectbox 学科筛选 + radio 选页，右侧 4 列 frontmatter 摘要卡（title/level/subject/updated）+ 完整 frontmatter JSON expander + 正文 bordered container + **反向链接区**（自带 60 字符上下文片段）；(3) **log 状态机三栏** — 🟢 active / 🟡 paused / ⚪ done 三列 + state 推断（feedback/schema-init 默认 done）+ 占位示例 toggle 可隐藏 + feedback/lint/schema-init 折叠到底部；(4) **Feedback Inbox** — 扫 `wiki/feedback/inbox/*.md` 列出待处理 ticket（过滤 README）。**严格只读定位**：不触发 wiki_write / wiki_index(rebuild=True)，底部明确提示重建命令。**验证链路**：streamlit server 起来 HTTP 200 / healthz OK；bare-mode `python dashboard/pages/phy_1_wiki.py` 全程无 traceback（仅 streamlit 正常的 ScriptRunContext 警告）；V1.6 冒烟测试 27/27 仍 PASS 无回归 |
| 2026-04-20 | V1.6 端到端冒烟测试 | 完成 | 实现 `tests/phy/test_v1_smoke.py`（约 320 行，零 lint，零外部依赖，stdlib unittest）。**27/27 PASS · 0.013s**。覆盖矩阵：(A) Mineru 纯函数 12 用例 — `_estimate_page_count` 4 种 case + `PAGE_RANGE_SOFT_LIMIT` 常量锁定 + `_rewrite_image_paths` markdown/HTML 双形式 + V1.3 双前缀回归 + 非图行保持 + CLI parser 三子命令；(B) Wiki 端到端 8 用例 — sources 摘要页创建、概念页 auto-fix（subject 推断 / created 注入 / updated 刷新）、read 回环含 frontmatter、search 全 5 scope（all/title/body/wikilink/subject）+ 无匹配信息、index dry-report 不写盘、rebuild 注入 AUTOGEN 段、**二次 rebuild 幂等替换语义**、断裂链接识别；(C) mode 隔离 6 用例 — runner 工具集严格 `{wiki_read, wiki_search}` / executor 同步 / builder 完整 4 个 / 未知 mode `ValueError` / OpenAI tools schema JSON 可序列化校验。**关键设计**：通过 monkeypatch `wiki.WIKI_ROOT` 到 tempdir 隔离真实 wiki；不打 MinerU 真 API（V1.4 已专项验证）。两种调用方式均通：`python tests/phy/test_v1_smoke.py` 与 `python -m unittest tests.phy.test_v1_smoke` |
| 2026-04-20 | 教材体系敲定 + 6 册 PDF 落位 | 完成 | 锁定**人教·新课标 2019 修订版（C 套）6 册**为高中主体导入对象（必修 1/2/3 + 选择性必修 1/2/3），全部 PDF（共 ~82MB）就位到 `res/phy/raw/pep/{required-1..3,elective-1..3}/full.pdf`；建立 `res/phy/raw/olympics-collections/` 接口预留目录与 README，**目标深度锁定 CPhO 决赛级，主体闭环后启动**（详见 PHY_PLAN.md 「竞赛进阶接入路线」段落）。同步更新 `res/phy/raw/README.md`（落位状态表）、`PHY_PLAN.md`（目录树 + V2 教材骨架 + 新增 C1-C5 竞赛子阶段 + 风险表）、`overview.md`（学科覆盖度按教材重映射 + 长期任务列出 C1-C4） |
| 2026-04-19 | V1.5 src/phy/wiki.py 四工具 | 完成 | 实现 `src/phy/wiki.py`（约 530 行，零 lint，零外部依赖）：(1) `wiki_read` 读 page_id 完整 markdown，含 frontmatter 解析、不存在时给"建议清单"、非法 id 拒大写；(2) `wiki_search` 五种 scope（all/title/body/wikilink/subject），wikilink 模式支持反向链接搜索；(3) `wiki_write` 最小 schema 校验（必填 title+level+id 对齐）+ 自动注入 created/updated + auto-fix 推断 subject + 不一致告警；(4) `wiki_index` 默认仅出统计报告，rebuild=true 才把 AUTOGEN 段写入 index.md 与 overview.md，**二次重建是替换而非追加**。手写极简 frontmatter 解析器避免引入 PyYAML。**mode 分级**：`get_tools(mode)` / `get_executors(mode)` 在注册时硬过滤，runner 模式 wiki_write/wiki_index 根本不出现在工具表。**自验 15/15 PASS** 含边界（断裂链接检测、subject 路径不一致 WARN、二次 rebuild 幂等）|
| 2026-04-19 | V1.4 mineru-tool.mdc 合规验证 + .ENV.example | 完成 | **合规矩阵 16/16 通过**：mode 标识 / file&url 双入口 / vlm 默认 / 强制 page-ranges / lightweight 兜底 / 图片整迁 / 路径重写 / 公式默认开 / 错误码全表 / Key 来源 .ENV / 找不到时退出 / full.md 重命名 / 8 步 ingest 第 2 步契约。**新增 30 页软上限警告**（`_estimate_page_count` 8/8 单测 + CLI 真触发）。**完善 `.ENV.example`**：`REPLACE_ME_WITH_REAL_*` 占位符 + 双向自检命令（真 .ENV 通过 / 占位符拒绝） + 注释含申请链接、配额、运行模式。**.gitignore** 已锁死 `.ENV / .env / *.env`（git check-ignore 验证） |
| 2026-04-19 | V1.3 移植 mineru.py | 完成 | 实现 `src/phy/tools/mineru.py`（558 行）：双 API（标准 v4 + 轻量 v1）、双入口（file 本地/url 远程）、强制 `--page-ranges` 守卫、`--allow-full` 紧急兜底；图片自动落到 `<source-stem>-images/` 并重写 md 内 `![](images/x)` 与 `<img src="images/x">` 两种引用；OSS 直传不带 Content-Type 规避 403；20+ 错误码中文友好提示；stdout 输出单行 JSON 摘要供 ingest 脚本消费。补充 `requirements.txt` 加 `requests>=2.31.0`，`src/phy/tools/__init__.py`。端到端真实链路验证（鉴权 / batch 申请 / OSS PUT / 状态轮询 / 错误码透传全部跑通） + 5/5 图片路径重写单测全过 + 4 项守卫验证（缺参/缺文件/非法 model/紧急兜底）|
| 2026-04-19 | V1.2 建立 wiki 三件套骨架 | 完成 | 创建 `res/phy/wiki/{index.md, log.md, overview.md}`：index 含双索引（按学科 / 按教材）+ 反向链接区 + 待补区域占位；log 含 schema-init 真实条目 + 三类格式示例（ingest 8 步状态机 / feedback 处理 / lint 报告）；overview 含统计表 + 学科覆盖度 + level 分布 + 短中长期建设方向 + 缺口区。三文件 frontmatter 严格遵守 schema §1.4（id/title/level: meta/created/updated），dogfood 自检过 §8 清单 |
| 2026-04-19 | V1.1 编写 PHYSICS_SCHEMA.md | 完成 | 落地 wiki 操作手册：通用/概念页/资料摘要页 frontmatter 字段、images & formulas 资产格式、wikilink 三种语法、log.md 三类条目（8 步 ingest / feedback / lint）完整模板、命名约定（kebab-case / 学科前缀 / 资料简称表）、3 套页面模板（concept basic / source / index）、9 项 lint 自检清单 |
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
