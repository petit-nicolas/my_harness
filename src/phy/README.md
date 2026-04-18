# src/phy — 物理教学 Agent 业务模块

本目录为 `vertical-industry` 分支物理教学子项目的代码入口，按 `PHY_PLAN.md` 的 V1-V7 逐步填充。

## 模块规划

| 模块 | 引入版本 | 职责 |
|------|----------|------|
| `wiki.py` | V1 | Wiki CRUD：`wiki_read` / `wiki_write` / `wiki_search` / `wiki_index` 工具实现 |
| `ingest.py` | V2 | `ingest_source`（PDF/MD/HTML → 抽概念 → 多页更新）+ `wiki_lint` |
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
