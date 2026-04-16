"""
Step 1.3 — Tool Calling 验证脚本
直接运行：python3 -m scripts.test_tool_calling
"""
import sys
import json

sys.path.insert(0, ".")

from src.client import chat

# ── 定义两个假工具（JSON Schema 格式）──────────────────────
FAKE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "读取指定路径的文件内容",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "要读取的文件路径",
                    }
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_shell",
            "description": "执行一条 shell 命令并返回输出",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "要执行的 shell 命令",
                    }
                },
                "required": ["command"],
            },
        },
    },
]


def test_tool_call_triggered() -> None:
    """验证：模型在需要时主动触发 tool_calls"""
    print("[测试 1/2] 模型主动触发工具调用")
    print("-" * 40)

    messages = [
        {"role": "user", "content": "帮我读取 README.md 文件的内容"}
    ]

    response = chat(messages, tools=FAKE_TOOLS)
    msg = response.choices[0].message

    # 验证模型返回了 tool_calls 而不是普通文本
    assert msg.tool_calls, "模型没有触发 tool_calls，请检查工具描述"

    tool_call = msg.tool_calls[0]
    func_name = tool_call.function.name
    func_args = json.loads(tool_call.function.arguments)

    print(f"工具名称：{func_name}")
    print(f"参数：{json.dumps(func_args, ensure_ascii=False, indent=2)}")
    print(f"tool_call_id：{tool_call.id}")
    print(f"finish_reason：{response.choices[0].finish_reason}")
    print()

    assert func_name == "read_file", f"期望调用 read_file，实际：{func_name}"
    assert "path" in func_args, "缺少 path 参数"
    print("✓ tool_calls 结构正确")
    print()


def test_tool_result_round_trip() -> None:
    """验证：把工具结果追加到历史后，模型能正常继续对话"""
    print("[测试 2/2] 工具结果追回历史，对话继续")
    print("-" * 40)

    # 第一轮：触发工具调用
    messages = [
        {"role": "user", "content": "帮我列出当前目录的文件"}
    ]
    resp1 = chat(messages, tools=FAKE_TOOLS)
    assistant_msg = resp1.choices[0].message
    tool_call = assistant_msg.tool_calls[0]

    print(f"模型触发工具：{tool_call.function.name}")

    # 第二轮：把工具执行结果追加到历史
    messages.append(assistant_msg)           # 追加 assistant 消息（含 tool_calls）
    messages.append({                        # 追加工具结果
        "role": "tool",
        "tool_call_id": tool_call.id,
        "content": "文件列表：README.md  src/  dashboard/  requirements.txt",
    })

    # 第三轮：让模型根据工具结果给出最终回答
    resp2 = chat(messages, tools=FAKE_TOOLS)
    final = resp2.choices[0].message.content

    print(f"模型最终回复：{final}")
    print(f"finish_reason：{resp2.choices[0].finish_reason}")
    print()

    assert resp2.choices[0].finish_reason == "stop", "期望 finish_reason=stop"
    assert final, "最终回复不能为空"
    print("✓ 工具结果回传后对话正常继续")
    print()


if __name__ == "__main__":
    print("=" * 40)
    print("  Tool Calling 验证")
    print("=" * 40)
    print()
    try:
        test_tool_call_triggered()
        test_tool_result_round_trip()
        print("✓ 所有 Tool Calling 测试通过")
    except AssertionError as e:
        print(f"✗ 断言失败：{e}")
        sys.exit(1)
    except Exception as e:
        print(f"✗ 异常：{e}")
        sys.exit(1)
