# Harness 项目上下文

## 项目简介

这是一个教学框架，从零实现类似 Claude Code 的极简 Coding Agent。
使用阿里千问 API（OpenAI 兼容模式），Python 3.11+ 编写。

## 目录结构

- `src/` — Agent 核心代码
- `dashboard/` — Streamlit 教学仪表盘
- `res/` — Claude Code 架构研究文档（12 份 PDF）
- `PLAN.md` — 完整实施计划
- `PROGRESS.md` — 实时进度追踪

## 当前阶段

准备阶段 Step 0，正在搭建项目基础设施。

## 运行方式

```bash
# 启动 Agent CLI
python -m src.main

# 启动教学仪表盘
streamlit run dashboard/app.py
```

## 注意事项

- API 密钥在 `.ENV` 文件中，不要提交到 git
- 每个 Step 完成后通过 `git tag step-X` 封版
