# src/phy — 物理教学 Agent 业务模块

本目录为 `vertical-industry` 分支物理教学子项目的代码入口，按 `PHY_PLAN.md` 的 V1-V7 逐步填充。

## 模块规划

| 模块 | 引入版本 | 职责 |
|------|----------|------|
| `tools/mineru.py` | V1 | MinerU API 封装（PDF/DOC/PPT/HTML → Markdown + images），物理特化（默认 vlm + 强制 page-ranges + 图片归位 + markdown 路径重写） |
| `wiki.py` | V1 | Wiki CRUD：`wiki_read` / `wiki_write` / `wiki_search` / `wiki_index` 四工具 |
| `wiki.py`（增量） | V2 | 追加 `wiki_lint`：孤儿页 / 缺图 / 公式冲突 / frontmatter 校验 / wikilink 断裂 |
| `ingest.py` | V2 | 8 步状态机编排 `ingest_chapter`：init_log → mineru_parse → read → split_review(reviewer) → create_source → create_concepts → update_index → lint |
| `reviewers/` | V2 起 | Reviewer Persona 配置目录，`call_reviewer(persona_id, payload)` 通用入口；详见同目录 README |
| `physics_prompt.md` | V3 | 顶级教师人格 + 教学原则 + wiki 使用守则 |
| `strategies.py` | V3 | `teach_analogy` / `teach_derivation` / `teach_misconception` 策略工具 |
| `student.py` | V4 | `StudentMap` 数据结构 + `student_get/update/assess` 工具 + 自动评估 hook |
| `render.py` | V5 | `render_demo`（模板 + 参数 → HTML）+ `render_plot`（Plotly） |
| `quiz.py` | V6 | `quiz_generate` / `quiz_evaluate` + 错题本 + IRT-lite 难度调节 |

## 接入约定

- **不修改** `src/agent.py` / `src/tools.py` 等主线代码
- 所有物理专属工具通过 `src/prompt.py` 的 `--mode physics` 分支按需加载
- 每次新增模块附带对应测试（`tests/phy/test_*.py`，V1 开始）

## 当前状态

**仅骨架**（本 README + `__init__.py`），业务实现从 V1 开始。
