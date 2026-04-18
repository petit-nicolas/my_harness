# res/phy/raw — 原始资料（不可变）

物理教材、讲义、历年题等一手资料的存放点。**只读**，作为 wiki 页面的溯源锚点（`frontmatter.sources`）。

## 目录规划（V2 开始填充）

```
raw/
├── pep-textbook-v1/         # 人教版高中物理（必修 + 选修）
├── olympics-collections/    # 竞赛相关资料（CPhO、IPhO 等）
└── misc/                    # 其他参考资料
```

## 放入规则

- 文件路径一旦被 wiki 页面引用，**不得改名或删除**
- 支持格式：PDF、Markdown、HTML、纯文本
- 大文件（> 10 MB）考虑走 Git LFS 或放链接 + hash

## 当前状态

**空目录**，V2 实现 `ingest_source` 后开始吸收首批教材。
