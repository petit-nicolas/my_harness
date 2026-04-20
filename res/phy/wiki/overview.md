---
id: overview
title: Physics Wiki 覆盖度概览
level: meta
created: 2026-04-19
updated: 2026-04-19
---

# Physics Wiki 覆盖度概览

> **用途**：让 Builder 一眼看清"知识库当前覆盖到哪里、还差什么"。每次 ingest 完成后由 `wiki_index --rebuild` 自动刷新统计部分；建设方向部分由 Builder 手动维护。
>
> **写权限**：仅 Cursor Builder 可写；Harness Runner 只读。

---

## 知识库统计

<!-- BEGIN wiki_index AUTOGEN: do not edit by hand -->

## 自动生成 — 当前实际统计

- 概念页总数: **3**
- 资料摘要页总数: **0**
- 已 ingest 教材章节（按 sources/ 估算）: **0**
- 断裂链接: **1**

### 学科分布（实际）
- mechanics: 2 页
- optics: 1 页

### Level 分布（实际）
- basic: 3 页

<!-- END wiki_index AUTOGEN -->

> 由 `wiki_index` 工具自动统计填充。

| 指标 | 当前值 | 目标值 |
|------|--------|--------|
| 概念页总数 | 0 | basic ≥ 200 / advanced ≥ 80 / competition ≥ 50 |
| 资料摘要页 | 0 | 至少覆盖人教版必修+选修全套 |
| 已 ingest 教材章节 | 0 | 待 V2 启动后增长 |
| 包含图片资产的页面占比 | — | ≥ 80%（物理知识依赖视觉表达） |
| 包含核心公式的页面占比 | — | ≥ 60% |
| Lint 通过率 | — | 100%（任何 lint 失败都应 24h 内修复或转 ticket） |

---

## 学科覆盖度

> 已锁定教材体系：**人教·新课标 2019 修订版（C 套）6 册**，详见 `res/phy/raw/README.md`。

| 学科 | 概念页 | 进度 | 主要资料源 |
|------|--------|------|------------|
| 力学（mechanics） | 0 | 0% | 必修第一册（运动·力·牛顿定律）+ 必修第二册（曲线运动·万有引力·机械能）+ 选择性必修第一册（动量·机械振动） |
| 电磁学（electromagnetism） | 0 | 0% | 必修第三册（静电场·电路·磁场）+ 选择性必修第二册（电磁感应·交流电） |
| 光学（optics） | 0 | 0% | 选择性必修第一册（光的折射衍射偏振） |
| 热学（thermodynamics） | 0 | 0% | 选择性必修第三册（分子动理论·气体·热力学定律） |
| 近代物理（modern） | 0 | 0% | 选择性必修第三册（原子物理·原子核） |
| 竞赛进阶 | 0 | 0% | `olympics-collections/`（接口预留，主体闭环后启动，目标 CPhO 决赛级） |

---

## Level 分布

| Level | 数量 | 用途 |
|-------|------|------|
| basic | 0 | 高中必修 + 选择性必修主干 |
| advanced | 0 | 选修拓展 + 高考压轴题型 |
| competition | 0 | CPhO / IPhO 进阶 |
| meta | 4 | schema/physics + index + log + overview（本文件） |

---

## 建设方向（Builder 手动维护）

### 短期（V2 ~ V3）

- [ ] 吸收人教必修一第 3 章（力）→ 第 4 章（牛顿运动定律）
- [ ] 建立 mechanics 学科的核心概念骨架（约 20 个 basic 页）
- [ ] 验证 8 步 ingest 流水线 + Reviewer + 断点恢复
- [ ] 接入 Feedback Loop，处理首批 ticket

### 中期（V4 ~ V6）

- [ ] 力学覆盖完整（含动量、能量、振动、流体）
- [ ] 电磁学起步（库仑定律 → 高斯定律 → 法拉第电磁感应）
- [ ] StudentMap 节点 id 与 wiki 对齐（学生评估走通）
- [ ] 6 个核心 demo_templates 接入对应 wiki 页

### 长期（V7+ · 主体闭环后启动）

- [ ] 6 册新教材 ingest 全部完成 + lint 全绿（启动条件）
- [ ] **竞赛进阶接入**（目标深度：**CPhO 决赛级**，详见 `PHY_PLAN.md` 「竞赛进阶接入路线」段落）
  - [ ] C1：程稼夫《培优教程》力学篇 1-3 章 ingest
  - [ ] C2：competition level 概念/题型页骨架
  - [ ] C3：V6 quiz_generate 接竞赛难度档
  - [ ] C4：学生 wikimap 增加竞赛分支视图

---

## 已知缺口

> 由 `wiki_lint` 报告 + `feedback inbox` 中 `kind: gap` ticket 自动汇总。Builder 在每次 build session 启动时检查本节。

*（V1.5 工具就位后自动填充）*

---

## 修订历程（schema 演化）

| 日期 | 事件 | 备注 |
|------|------|------|
| 2026-04-19 | wiki 三件套骨架建立（V1.2） | schema/physics v1 + 三个 meta 单例 |
| 2026-04-20 | 教材体系敲定 | 锁定人教·新课标 2019 修订版 6 册；竞赛资料留接口（决赛级，主体闭环后启动） |
