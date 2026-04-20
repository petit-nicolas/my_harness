# res/phy/raw — 原始资料（不可变）

物理教材、讲义、历年题等一手资料的存放点。**只读**，作为 wiki 页面的溯源锚点（`frontmatter.sources` → `wiki/sources/` → 这里）。

## 目录规划（V1 末已落地高中主体；竞赛部分 V6 起填充）

```
raw/
├── pep/                       # 人民教育出版社·新课标 2019 修订版
│   ├── required-1/            # 必修第一册（运动·力·牛顿运动定律）
│   │   ├── full.pdf           # 原 PDF（已就位 ✅）
│   │   ├── ch3.md             # MinerU vlm 解析结果（V2 起按章节生成）
│   │   └── ch3-images/        # MinerU 提取的插图
│   ├── required-2/            # 必修第二册（曲线运动·万有引力·机械能）
│   ├── required-3/            # 必修第三册（静电场·电路·磁场）
│   ├── elective-1/            # 选择性必修第一册（动量·机械振动·光）
│   ├── elective-2/            # 选择性必修第二册（电磁感应·交流电）
│   └── elective-3/            # 选择性必修第三册（热学·原子物理）
├── olympics-collections/      # 竞赛资料（V6 起逐步填充，目标深度：CPhO 决赛）
│   └── README.md              # 接入规划与三本核心资料清单
└── （后续可加 misc/ 等其他参考源）
```

## 放入规则

- 文件路径一旦被 wiki 页面或 ingest log 引用，**不得改名或删除**
- 单本教材统一使用 `full.pdf` 作为入口；解析产物（`<chN>.md` + `<chN>-images/`）平级落到该教材目录下
- 支持格式：PDF、Markdown、HTML、PNG/JPG、纯文本
- 大教材使用 `--page-ranges` 按章节分批解析，单批不超 30 页（mineru-tool.mdc 软上限）
- 图片输出位置：`raw/<subdir>/<source-stem>-images/`，不得散落到 `wiki/`

## 解析工具

由 `src/phy/tools/mineru.py`（V1 已就位）解析。详细使用规范见 `.cursor/rules/mineru-tool.mdc`：

```bash
# 例：解析必修一第 3 章（相互作用·力）
python -m src.phy.tools.mineru file "res/phy/raw/pep/required-1/full.pdf" \
    --output res/phy/raw/pep/required-1/ \
    --model vlm \
    --page-ranges 45-78
```

## 当前状态（V1 末）

| 教材 | 路径 | 状态 |
|------|------|------|
| 必修第一册 | `pep/required-1/full.pdf` | ✅ 14 MB 已就位，V2 首章 ingest 优先目标 |
| 必修第二册 | `pep/required-2/full.pdf` | ✅ 13 MB 已就位 |
| 必修第三册 | `pep/required-3/full.pdf` | ✅ 16 MB 已就位 |
| 选择性必修第一册 | `pep/elective-1/full.pdf` | ✅ 13 MB 已就位 |
| 选择性必修第二册 | `pep/elective-2/full.pdf` | ✅ 13 MB 已就位 |
| 选择性必修第三册 | `pep/elective-3/full.pdf` | ✅ 13 MB 已就位 |
| 竞赛资料 | `olympics-collections/` | ⏳ 接口已留，V6 起按 README 清单逐步导入 |
