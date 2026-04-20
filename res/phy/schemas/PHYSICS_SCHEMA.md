---
id: schema/physics
title: Physics Wiki Schema
level: meta
applies_to: res/phy/wiki/**/*.md
created: 2026-04-19
updated: 2026-04-19
---

# Physics Wiki Schema

本文档是物理知识 wiki 的**操作手册**。所有 wiki 页面必须遵守。

> **设计原则与边界**（知识严谨性、教师人格、Builder/Runner 二分、Reviewer Persona、Feedback Loop）见 `.cursor/rules/physics-project.mdc`。本文档专注**字段定义、模板示例、命名约定**这些操作细节，不重复高层规则。

---

## 0. 术语速查

| 术语 | 含义 |
|------|------|
| **概念页** | `wiki/<subject>/<id>.md`，单个物理概念/原理/题型的权威页面 |
| **资料摘要页** | `wiki/sources/<source-id>.md`，每次 ingest 产出，桥接 raw 与概念页 |
| **id** | 页面唯一标识，等于相对 `wiki/` 的路径（不含 `.md`），如 `mechanics/newton-second-law` |
| **subject** | 学科分类目录，固定为 `mechanics` / `electromagnetism` / `thermodynamics` / `optics` / `modern` |
| **wikilink** | `[[id]]` 形式的内部双向链接 |

---

## 1. Frontmatter 字段

### 1.1 通用字段（所有页面必填）

| 字段 | 类型 | 必填 | 说明 |
|------|------|:---:|------|
| `id` | str | ✅ | 与文件路径对齐：`<dir>/<stem>` |
| `title` | str | ✅ | 中文标题（用于显示，不参与 id 生成） |
| `level` | enum | ✅ | `basic` \| `advanced` \| `competition` \| `meta` |
| `created` | date | ✅ | ISO 日期 `YYYY-MM-DD` |
| `updated` | date | ✅ | 每次修改时同步更新 |
| `status` | enum | ❌（默认 `active`） | `active` \| `draft` \| `superseded` \| `proposed` |

### 1.2 概念页专用字段（`wiki/<subject>/*.md`）

| 字段 | 类型 | 必填 | 说明 |
|------|------|:---:|------|
| `prerequisites` | list[id] | ✅（可空 `[]`） | 学习本页前应掌握的概念页 id |
| `sources` | list[wikilink] | ✅（至少 1 项） | 链回 `[[sources/<source-id>]]`，**不直接引用 raw** |
| `images` | list[obj] | ❌ | 详见 §4.1 |
| `formulas` | list[obj] | ❌ | 详见 §4.2 |
| `tags` | list[str] | ❌ | 自由分类标签 |

### 1.3 资料摘要页专用字段（`wiki/sources/*.md`）

| 字段 | 类型 | 必填 | 说明 |
|------|------|:---:|------|
| `raw_path` | str | ✅ | 对应 raw 文件相对仓库根的路径，如 `res/phy/raw/pep/v1/full.pdf` |
| `markdown_path` | str | ✅ | MinerU 输出 markdown 路径 |
| `images_dir` | str | ❌ | MinerU 输出图片目录，无图省略 |
| `page_ranges` | str | ✅ | 本次 ingest 覆盖的页范围，如 `45-78` |
| `covers` | list[id] | ✅ | 本次 ingest 创建/更新的概念页 id 列表 |
| `ingest_log_ref` | str | ✅ | 链回 `wiki/log.md` 中对应 ingest 条目的标题锚点 |

### 1.4 索引/日志/概览页（单例 meta 文件）

`index.md` / `log.md` / `overview.md` 不强制完整 frontmatter，但建议至少有 `title` 和 `updated`。

---

## 2. 正文结构

### 2.1 概念页推荐结构

```markdown
# <title>

## 一句话定义
（30 字以内的精确定义，包含核心要素）

## 数学表述
（公式 + 每个符号的物理意义）

## 适用条件
（必须明确列出近似域、坐标系、参考系等约束）

## 物理图像
（intuition：让学生在脑中能"看见"这个概念）

## 典型例题
（1-3 个最能体现核心思想的题目，附完整解答）

## 常见误区
（学生最容易踩的坑，每条配反例）

## 相关演示
（链接到 V5 之后建立的 demo_templates 实例，本阶段可写"待补"）

## 进阶（可选）
（competition level 才需要：严密推导、与高等物理的衔接）
```

### 2.2 资料摘要页推荐结构

```markdown
# <title>

## 资料概述
（一段话说明这是什么资料、覆盖什么范围）

## 核心要点
（要点列表，每条对应一个或多个概念页）

## 知识点覆盖
（按本次 ingest 覆盖的概念，列出 wikilink）

## 图片清单
（每张图的 caption + 在哪个概念页被引用）

## 公式清单
（每个核心公式 + 在哪个概念页被定义）
```

---

## 3. Wikilink 与引用

### 3.1 基本语法

| 语法 | 含义 |
|------|------|
| `[[mechanics/force]]` | 链接到 `wiki/mechanics/force.md` |
| `[[mechanics/force#矢量性]]` | 链接到该页"矢量性"小节 |
| `[[mechanics/force\|力（矢量）]]` | 自定义显示文本 |
| `[[sources/pep-v1-ch3]]` | 链接到资料摘要页 |

### 3.2 引用规则

- **首次提及**某个有独立页面的概念，**必须**用 wikilink；后续提及可用普通文本
- 不允许指向不存在的页面（断链由 `wiki_lint` 检测）
- 反向链接（"哪些页面引用了我"）由 `wiki_index` 工具自动维护到 `index.md` 与各页底部，**不手写**

### 3.3 跨学科引用

- 跨学科引用必须使用全 id：`[[modern/special-relativity]]`，不可省略 subject 前缀
- sources 页可被多个学科的概念页引用（如同一章节同时涵盖力学和电磁学）

---

## 4. 图片与公式资产

### 4.1 `images` 字段格式

```yaml
images:
  - path: ../../raw/pep/v1/ch3-images/img-012.png
    caption: 受力分析示例（小球沿斜面下滑）
    page: 47                # 来源 raw 文件中的页码（int）
    role: example           # example | derivation | apparatus | misconception
```

| 字段 | 必填 | 说明 |
|------|:---:|------|
| `path` | ✅ | **相对当前 .md 文件**的路径，必须落在 `res/phy/raw/<source>/<stem>-images/` 内 |
| `caption` | ✅ | 中文图注，与正文 alt text 必须一致 |
| `page` | ❌ | raw 文件中的来源页码 |
| `role` | ✅ | 用途分类：例题 / 推导 / 装置 / 误区 |

### 4.2 `formulas` 字段格式

```yaml
formulas:
  - latex: "\\vec{F} = m\\vec{a}"
    name: 牛顿第二定律
    condition: 非相对论近似
    role: definition        # definition | derivation | result
```

| 字段 | 必填 | 说明 |
|------|:---:|------|
| `latex` | ✅ | LaTeX 源码（YAML 中转义反斜杠为 `\\`） |
| `name` | ✅ | 公式中文名 |
| `condition` | ❌ | 适用条件（如"非相对论近似"、"小角度近似"） |
| `role` | ✅ | 角色：定义 / 推导步骤 / 结论 |

### 4.3 正文中的图片与公式

**图片**（标准 markdown，不依赖 frontmatter）：

```markdown
![受力分析示例（小球沿斜面下滑）](../../raw/pep/v1/ch3-images/img-012.png)
```

**公式**：

| 类型 | 语法 | 示例 |
|------|------|------|
| 行内 | `\(...\)` 或 `$...$` | 速度 $v = \frac{ds}{dt}$ |
| 块级 | `\[...\]` 或 `$$...$$` | `$$\vec{F} = m\vec{a}$$` |

**约束**：

- 首次出现某符号必须紧跟定义（如"$v$ 为瞬时速度"）
- 适用条件必须紧跟公式，不能藏在远处
- 矢量统一用 `\vec{}` 或 `\mathbf{}`，全文一致

---

## 5. log.md 条目格式

`wiki/log.md` 顶部追加新条目（最新在最上）。共三类条目，使用统一前缀便于检索。

### 5.1 Ingest 条目（8 步状态机）

```markdown
## [2026-04-19] ingest | 人教版必修一 第三章 力

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
    - reviewed_at: 2026-04-19T11:02:33
- **user_guidance**: |
    重点拆"力的合成与分解"，先不做"摩擦力"。
    建议把"力的图示"和"力的示意图"合并到 force 主页面而非独立页。
- **splits**:
    - {id: mechanics/force, title: 力的概念, focus: 矢量性, skip: false}
    - {id: mechanics/force-composition, title: 力的合成, focus: 平行四边形定则, skip: false}
    - {id: mechanics/friction, title: 摩擦力, focus: -, skip: true}
- **steps**:
    - [x] 1. 初始化日志
    - [x] 2. MinerU 解析
    - [x] 3. 阅读资料
    - [x] 4. 拆分粒度评审
    - [ ] 5. 创建 sources 摘要
    - [ ] 6. 创建概念页
    - [ ] 7. 更新索引
    - [ ] 8. lint 检查
```

**state 取值**：

| state | 含义 | 下次启动行为 |
|-------|------|--------------|
| `active` | 正在某步执行（崩溃/中断时停在此态） | 从最后一个 `[x]` 的下一步继续 |
| `paused` | 等待外部输入（如 reviewer 失败需重跑） | 报告用户后再决定继续/放弃 |
| `done` | 全部完成 | 跳过本条 |

**条目完成后**简化为最终形态（保留摘要信息，删除步骤清单）：

```markdown
## [2026-04-19] ingest | 人教版必修一 第三章 力

- **source**: `res/phy/raw/pep/v1/full.pdf` (45-78)
- **state**: done
- **created**: sources/pep-v1-ch3, mechanics/force, mechanics/force-composition, mechanics/force-decomposition, mechanics/elastic-force, mechanics/gravity
- **updated**: index.md, overview.md
- **duration_total_s**: 412
```

### 5.2 Feedback Processing 条目

```markdown
## [2026-04-19] feedback | mechanics/newton-second-law | accepted

- **ticket_id**: 2026-04-19T10-32-15-a3f2
- **target**: mechanics/newton-second-law
- **kind**: unclear
- **reviewer**:
    - persona: feedback_reviewer
    - executor: cursor
    - confidence: 0.92
- **decision**: accept
- **commit_summary**: 在适用条件段加醒目提示框；新增"高速场景"段落链接 [[modern/special-relativity]]
- **updated_pages**: mechanics/newton-second-law
- **processed_at**: 2026-04-19T15:44:02
```

`decision` 取 `accept | reject | needs_more_info`，对应 ticket 的归宿（详见 `wiki/feedback/README.md`）。

### 5.3 Lint 条目

```markdown
## [2026-04-19] lint | weekly check

- **state**: done
- **run_at**: 2026-04-19T20:00:00
- **summary**: {orphan: 0, missing_images: 1, formula_conflict: 0, broken_link: 2, missing_field: 0}
- **issues**:
    - {kind: missing_images, page: mechanics/spring-oscillation, detail: "frontmatter 引用 img-007.png 但文件不存在"}
    - {kind: broken_link, page: mechanics/circular-motion, detail: "[[mechanics/centripetal-force]] 目标页未创建"}
- **next_action**: 已在 wiki/feedback/inbox/ 自动 submit 2 条 ticket
```

---

## 6. 命名约定

### 6.1 文件名 / id

- 一律小写英文 + 连字符（kebab-case）
- 与中文术语的对应关系由 `index.md` 维护，不进文件名

| 类型 | 模式 | 示例 |
|------|------|------|
| 概念页 | `<subject>/<topic>.md` | `mechanics/newton-second-law.md` |
| 资料摘要页 | `sources/<publisher>-<volume>-<chapter>.md` | `sources/pep-v1-ch3.md` |
| 比较页（可选） | `comparisons/<topic-a>-vs-<topic-b>.md` | `comparisons/momentum-vs-energy.md` |
| 学生提议（V3 后） | `proposed/<short-id>.md` | `proposed/quantum-entanglement.md` |

### 6.2 子目录前缀

| 学科 | 目录 | 涵盖 |
|------|------|------|
| 力学 | `mechanics/` | 运动学、动力学、振动、流体 |
| 电磁学 | `electromagnetism/` | 静电、稳恒电流、磁场、电磁感应 |
| 热学 | `thermodynamics/` | 分子动理论、热力学定律、热传递 |
| 光学 | `optics/` | 几何光学、波动光学 |
| 近代物理 | `modern/` | 相对论、量子、原子物理 |

### 6.3 资料简称

| 出版方/来源 | 简称 | 示例 id |
|--------------|------|---------|
| 人民教育出版社 | `pep` | `pep-v1-ch3` |
| 教育科学出版社 | `pek` | `pek-v2-ch5` |
| CPhO（中国物理奥赛） | `cpho` | `cpho-2024-mechanics` |
| IPhO（国际物理奥赛） | `ipho` | `ipho-2023-experimental` |

---

## 7. 完整页面模板

### 7.1 概念页模板（basic level）

```markdown
---
id: mechanics/newton-second-law
title: 牛顿第二定律
level: basic
created: 2026-04-19
updated: 2026-04-19
status: active
prerequisites:
  - mechanics/force
  - mechanics/mass
sources:
  - "[[sources/pep-v1-ch3]]"
images:
  - path: ../../raw/pep/v1/ch3-images/img-012.png
    caption: 受力分析示例
    page: 47
    role: example
formulas:
  - latex: "\\vec{F} = m\\vec{a}"
    name: 牛顿第二定律
    condition: 非相对论近似
    role: definition
tags: [力学, 经典力学, 高中必修一]
---

# 牛顿第二定律

## 一句话定义
物体加速度大小与所受合外力成正比、与质量成反比，方向与合外力相同。

## 数学表述
$$\vec{F} = m\vec{a}$$

其中 $\vec{F}$ 为合外力（矢量），$m$ 为物体的惯性质量，$\vec{a}$ 为加速度（与合外力同向的矢量）。

## 适用条件
- 非相对论近似（$v \ll c$）
- 物体可视为质点
- 在惯性系中观察
- $m$ 视为常数（变质量系统需用动量形式 $\vec{F} = \frac{d\vec{p}}{dt}$）

## 物理图像
![受力分析示例](../../raw/pep/v1/ch3-images/img-012.png)

想象一个质量为 $m$ 的小球放在光滑水平面上：
- 推它一下（施加 $\vec{F}$）→ 它会向推的方向加速
- 推力越大，加速越快（线性关系）
- 同样的力作用在更重的物体上 → 加速度更小

## 典型例题
（略，按需填入）

## 常见误区
- 错将"力维持运动"当作牛二的内涵（这是亚里士多德观点，与之相反）
- 把瞬时关系误用为非瞬时（$\vec{F}(t)$ 和 $\vec{a}(t)$ 必须同时刻取值）

## 相关演示
（待 V5 后链接到 demo_templates 实例）

## 参考资料
- [[sources/pep-v1-ch3]] §3.4
```

### 7.2 资料摘要页模板

```markdown
---
id: sources/pep-v1-ch3
title: 人教版必修一 第三章 — 相互作用·力
level: meta
created: 2026-04-19
updated: 2026-04-19
status: active
raw_path: res/phy/raw/pep/v1/full.pdf
markdown_path: res/phy/raw/pep/v1/ch3.md
images_dir: res/phy/raw/pep/v1/ch3-images/
page_ranges: 45-78
covers:
  - mechanics/force
  - mechanics/force-composition
  - mechanics/force-decomposition
  - mechanics/elastic-force
  - mechanics/gravity
ingest_log_ref: "log.md#2026-04-19-ingest-人教版必修一-第三章-力"
---

# 人教版必修一 第三章 — 相互作用·力

## 资料概述
本章系统介绍力的基本概念、矢量性，以及高中物理中常见的几种力（重力、弹力、摩擦力）和力的合成分解方法。

## 核心要点
1. 力是物体间的相互作用，具有矢量性（[[mechanics/force]]）
2. 力的合成遵循平行四边形定则（[[mechanics/force-composition]]）
3. ……

## 知识点覆盖
- [[mechanics/force]] — 力的概念与矢量性
- [[mechanics/force-composition]] — 力的合成
- [[mechanics/force-decomposition]] — 力的分解
- [[mechanics/elastic-force]] — 弹力
- [[mechanics/gravity]] — 重力

## 图片清单
| 图 | caption | 出现在 |
|----|---------|--------|
| img-008 | 力的图示 | [[mechanics/force]] |
| img-012 | 受力分析示例 | [[mechanics/newton-second-law]] |

## 公式清单
| 公式 | 名称 | 出现在 |
|------|------|--------|
| $\vec{F} = m\vec{a}$ | 牛顿第二定律 | [[mechanics/newton-second-law]] |
| $\vec{F} = \vec{F_1} + \vec{F_2}$ | 力的合成 | [[mechanics/force-composition]] |
```

### 7.3 索引页模板（index.md 骨架）

```markdown
---
title: Physics Wiki 索引
updated: 2026-04-19
---

# Physics Wiki 索引

## 按学科

### 力学
- [[mechanics/force]] — 力的定义、矢量性、典型分类

### 电磁学
（待补）

### 热学 / 光学 / 近代物理
（待补）

## 按教材

### 人教版·必修一
- 第 3 章 [[sources/pep-v1-ch3]] — 5 个概念页

## 待补区域
（由 wiki_lint 自动汇总，不手写）
```

---

## 8. Schema 自检清单（lint 必查）

每个 wiki 页面在 `wiki_lint` 检查时，按以下顺序自检：

- [ ] frontmatter 所有"必填"字段齐全
- [ ] `id` 与文件路径一致
- [ ] `created` ≤ `updated`
- [ ] `prerequisites` 中每个 id 实际存在
- [ ] `sources` 中每个 wikilink 实际存在
- [ ] `images.path` 文件实际存在，且在 raw 目录内
- [ ] 正文 alt text 与 frontmatter `caption` 一致
- [ ] 正文 wikilink 目标实际存在
- [ ] 公式 LaTeX 可解析（不出现裸的 `\vec` 等未闭合命令）
- [ ] 矢量符号风格全文一致（`\vec` 与 `\mathbf` 不混用）

---

## 9. 演化原则

- 本 schema 本身遵守 wiki 规则（dogfood）：本文件 frontmatter 完整、自身可被 lint 检查
- schema 升级时同步更新所有现有页面（由 Cursor 在 build-time 批量执行）
- 升级记录追加到 `wiki/log.md` 的 `schema-update` 类条目（第四类条目，未来扩展）
