# res/phy/wiki — 物理知识权威图谱

由 LLM 通过工具维护的结构化知识库。所有写操作走 8 步 ingest 流水线（V2 落地），状态持久化在 `log.md` 中支持断点恢复。

## 目录规划（V1 之后填充）

```
wiki/
├── index.md            # 双索引：按学科 + 按教材章节
├── log.md              # 8 步 ingest 状态机日志（active/paused/done）
├── overview.md         # 知识库覆盖度与待补区域
├── sources/            # 每次 ingest 的章节摘要页（桥接 raw 与 wiki）
│   └── pep-v1-ch3.md   # 例：人教版必修一第三章摘要
├── feedback/           # Runner→Builder 反馈队列（V3 引入）
│   ├── inbox/          # 待处理（Harness Runner 只能 append）
│   ├── processed/      # 已接受并修订（仅 Cursor Builder 可写）
│   └── rejected/       # 拒绝（仅 Cursor Builder 可写）
├── mechanics/          # 力学
├── electromagnetism/   # 电磁学
├── thermodynamics/     # 热学
├── optics/             # 光学
└── modern/             # 近代物理
```

## 写作规范

见 `res/phy/schemas/PHYSICS_SCHEMA.md`（V1 建立）与 `.cursor/rules/physics-project.mdc`。

每个 `.md` 页面 frontmatter 必填：`id` / `title` / `level` / `prerequisites` / `sources` / `images` / `formulas` / `updated`。

## sources/ 摘要层的作用

- **桥接** `raw/` 原始资料和 `wiki/<subject>/` 学科概念页
- 每次 ingest 产出**至少一个** sources 页（如 `sources/pep-v1-ch3.md`）
- 概念页 frontmatter 的 `sources:` 字段引用 sources 页（而非直接引用 raw）
- 修订溯源走"概念页 → sources 页 → raw 文件"三跳

## Builder / Runner 写权限

- **Builder（Cursor Agent）**：所有子目录可读写
- **Runner（Harness Agent）**：除 `feedback/inbox/`（仅 append）外，其余路径**只读**
- 通过 `src.security` file policy 实现硬隔离，不依赖 prompt 约束

## 当前状态

**空目录**，等待 V1.2 子任务建立首个 schema 与索引/日志/概览骨架。Feedback 子目录由 V3 子任务建立。
