# res/phy/raw — 原始资料（不可变）

物理教材、讲义、历年题等一手资料的存放点。**只读**，作为 wiki 页面的溯源锚点（`frontmatter.sources` → `wiki/sources/` → 这里）。

## 目录规划（V1 工具就位、V2 开始填充）

```
raw/
├── pep/                       # 人民教育出版社
│   ├── v1/                    # 必修一
│   │   ├── full.pdf           # 原 PDF
│   │   ├── ch3.md             # MinerU vlm 解析结果
│   │   └── ch3-images/        # MinerU 提取的插图
│   │       ├── img-001.png
│   │       └── ...
│   └── v2/                    # 必修二
├── olympics-collections/      # 竞赛资料（CPhO / IPhO）
└── misc/                      # 其他参考
```

## 放入规则

- 文件路径一旦被 wiki 页面或 ingest log 引用，**不得改名或删除**
- 支持格式：PDF、Markdown、HTML、PNG/JPG、纯文本
- 大教材使用 `--page-ranges` 按章节分批解析，单批不超 30 页
- 图片输出位置：`raw/<subdir>/<source-stem>-images/`，不得散落到 `wiki/`

## 解析工具

由 `src/phy/tools/mineru.py`（V1 引入）解析。详细使用规范见 `.cursor/rules/mineru-tool.mdc`：

```bash
python src/phy/tools/mineru.py file "res/phy/raw/pep/v1/full.pdf" \
    --output res/phy/raw/pep/v1/ \
    --model vlm \
    --page-ranges 45-78
```

## 当前状态

**仅放置参考方案 PDF**（`../LLM Wiki.pdf`），V2 启动后由用户提供首批教材，Agent 自行 ingest。
