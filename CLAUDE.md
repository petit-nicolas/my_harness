# 项目约定

## 技术栈

- Python 3.11+，所有源码在 `src/` 目录下
- 入口：`python -m src.main`
- 依赖管理：`requirements.txt`，使用 `.venv` 虚拟环境

## 代码规范

- 命名：函数/变量 snake_case，类 PascalCase，常量 UPPER_SNAKE_CASE
- 类型注解：所有公开函数必须标注参数和返回值类型
- 注释：用中文说明"为什么"，不解释"做了什么"
- 导入顺序：标准库 → 第三方库 → 项目内部模块

## 目录结构

```
src/
├── client.py       # 千问 API 客户端（单例，chat() 统一接口）
├── prompt.py       # 提示词组装器（build_system_prompt）
├── system_prompt.md# 系统提示词模板（含占位符）
├── tools.py        # 工具注册表 + 执行器（Step 3 实现）
├── agent.py        # Agent 主循环（Step 3 实现）
└── cli.py          # REPL 界面（Step 3 实现）
```

## 工具开发约定

新增工具时，在 `src/tools.py` 中注册，格式：

```python
{
    "type": "function",
    "function": {
        "name": "tool_name",
        "description": "一句话说清楚这个工具做什么",
        "parameters": { ... }   # JSON Schema
    }
}
```

## 错误处理

- API 调用失败：抛出具体异常，不要裸 `except`
- 文件操作：使用 `pathlib.Path`，路径不存在时给出清晰提示
- 工具执行失败：返回错误字符串，不要让 agent 循环崩溃
