---
id: log
title: Physics Wiki 操作日志
level: meta
created: 2026-04-19
updated: 2026-04-19
---

# Physics Wiki 操作日志

> **使用规则**（详见 [`../schemas/PHYSICS_SCHEMA.md`](../schemas/PHYSICS_SCHEMA.md) §5）：
>
> - **新条目追加在顶部**（最新在最上）
> - 共三类条目：`ingest` / `feedback` / `lint`，前缀严格一致便于检索
> - `ingest` 条目随状态机推进多次更新；完成后简化为最终形态
> - **断点恢复协议**：每次 build session 启动时，Cursor 必须先扫本文件，发现 `state: active|paused` 的 ingest 条目时优先恢复（不允许并发新建）
>
> **写权限**：仅 Cursor Builder 可写；Harness Runner 只读。

---

## [2026-04-19] schema-init | 初始化 wiki 三件套

- **state**: done
- **created**: index.md, log.md, overview.md
- **schema_ref**: schemas/PHYSICS_SCHEMA.md（V1.1 建立）
- **summary**: V1.2 建立 wiki 骨架，等待 V1.3 MinerU 工具就位 + V1.5 wiki 四工具就位后开始 V2 真实 ingest

---

<!--
================================================================
以下三条为格式示例，标注「占位/示例」字样，**不代表真实内容**。
V2 第一次实跑前可保留作为模板参照；首次真实 ingest 完成后可删除。
================================================================
-->

## [示例] [YYYY-MM-DD] ingest | 人教版必修一 第三章 力（占位示例）

- **source**: `res/phy/raw/pep/v1/full.pdf`
- **page_ranges**: 45-78
- **state**: paused
- **mineru**:
    - model: vlm
    - output_md: `res/phy/raw/pep/v1/ch3.md`
    - output_images: `res/phy/raw/pep/v1/ch3-images/` (12 张)
    - duration_s: 87
- **reviewer**:
    - persona: physics_teacher_reviewer
    - executor: cursor
    - confidence: 0.86
    - reviewed_at: YYYY-MM-DDT11:02:33
- **user_guidance**: |
    （示例）重点拆"力的合成与分解"，先不做"摩擦力"。
- **splits**:
    - {id: mechanics/force, title: 力的概念, focus: 矢量性, skip: false}
    - {id: mechanics/force-composition, title: 力的合成, focus: 平行四边形定则, skip: false}
- **steps**:
    - [x] 1. 初始化日志
    - [x] 2. MinerU 解析
    - [x] 3. 阅读资料
    - [x] 4. 拆分粒度评审
    - [ ] 5. 创建 sources 摘要
    - [ ] 6. 创建概念页
    - [ ] 7. 更新索引
    - [ ] 8. lint 检查

---

## [示例] [YYYY-MM-DD] feedback | mechanics/newton-second-law | accepted（占位示例）

- **ticket_id**: YYYY-MM-DDT10-32-15-a3f2
- **target**: mechanics/newton-second-law
- **kind**: unclear
- **reviewer**:
    - persona: feedback_reviewer
    - executor: cursor
    - confidence: 0.92
- **decision**: accept
- **commit_summary**: 在适用条件段加醒目提示框；新增"高速场景"段落链接 [[modern/special-relativity]]
- **updated_pages**: mechanics/newton-second-law
- **processed_at**: YYYY-MM-DDT15:44:02

---

## [示例] [YYYY-MM-DD] lint | weekly check（占位示例）

- **state**: done
- **run_at**: YYYY-MM-DDT20:00:00
- **summary**: {orphan: 0, missing_images: 1, formula_conflict: 0, broken_link: 2, missing_field: 0}
- **issues**:
    - {kind: missing_images, page: mechanics/spring-oscillation, detail: "frontmatter 引用 img-007.png 但文件不存在"}
    - {kind: broken_link, page: mechanics/circular-motion, detail: "[[mechanics/centripetal-force]] 目标页未创建"}
- **next_action**: 已在 wiki/feedback/inbox/ 自动 submit 2 条 ticket
