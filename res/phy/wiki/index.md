---
id: index
title: Physics Wiki 索引
level: meta
created: 2026-04-19
updated: 2026-04-19
---

# Physics Wiki 索引

> **维护者**：本文件由 `wiki_index` 工具自动维护。Builder 手动修改后请重跑 `wiki_index --rebuild` 保持双索引一致。
>
> **写权限**：仅 Cursor Builder 可写；Harness Runner 只读。
>
> **完整字段约定**：见 [`../schemas/PHYSICS_SCHEMA.md`](../schemas/PHYSICS_SCHEMA.md)。

---

## 按学科

### 力学（mechanics）
*（待 V2 ingest 后填充）*

### 电磁学（electromagnetism）
*（待 V2 ingest 后填充）*

### 热学（thermodynamics）
*（待 V2 ingest 后填充）*

### 光学（optics）
*（待 V2 ingest 后填充）*

### 近代物理（modern）
*（待 V2 ingest 后填充）*

---

## 按教材

### 人教版（pep）
*（待 V2 ingest 后填充）*

| 教材 | 摘要页 | 概念页数 |
|------|--------|---------|
| *待补* | *待补* | *待补* |

### 竞赛资料（cpho / ipho）
*（待 V2 ingest 后填充，作为 advanced/competition level 内容来源）*

---

## 反向链接索引

<!-- BEGIN wiki_index AUTOGEN: do not edit by hand -->

## 自动生成 — 学科索引

### mechanics
- [[mechanics/force]] — 力
- [[mechanics/newton-second-law]] — 牛顿第二定律

### optics
- [[mechanics/odd]] — x

## 自动生成 — 反向链接

- **mechanics/force** ← 被引用 1 次
    - mechanics/newton-second-law
- **mechanics/newton-second-law** ← 被引用 1 次
    - mechanics/force

<!-- END wiki_index AUTOGEN -->

> 由 `wiki_index` 工具基于全量页面扫描自动生成。形如：
>
> ```
> mechanics/force ← 被引用 3 次：
>   - mechanics/newton-second-law
>   - mechanics/force-composition
>   - sources/pep-v1-ch3
> ```

*（V1.5 工具就位后自动填充）*

---

## 待补区域

> 由 `wiki_lint` 与 `feedback_resolve` 自动汇总，**不手写**：
>
> - lint 报告中 `kind: broken_link` 的目标页面
> - feedback inbox 中 `kind: gap` 或 `kind: new_concept` 的 ticket
> - sources 摘要页 `covers` 字段中尚未创建的概念页 id

*（V1.5 工具就位后自动填充）*
