# res/phy/wiki — 物理知识权威图谱

由 LLM 通过 `wiki_read` / `wiki_write` / `wiki_search` / `wiki_index` 工具维护的结构化知识库。

## 目录规划（V1 之后填充）

```
wiki/
├── index.md                 # 反向索引，wiki_index 工具自动维护
├── log.md                   # 所有写操作按时间追加记录
├── mechanics/               # 力学
├── electromagnetism/        # 电磁学
├── thermodynamics/          # 热学
├── optics/                  # 光学
└── modern/                  # 近代物理
```

## 写作规范

见 `res/phy/schemas/PHYSICS_SCHEMA.md`（V1 建立）与 `.cursor/rules/physics-project.mdc` 的"Wiki 写作风格"段落。

每个 `.md` 页面必须包含 frontmatter：`id`、`title`、`level`、`prerequisites`、`sources`、`updated`。

## 当前状态

**空目录**，等待 V1 封版后填入首个 schema 与索引骨架。
