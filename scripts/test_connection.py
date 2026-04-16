"""
Step 1.2 — 连通性验证脚本
直接运行：python3 -m scripts.test_connection
"""
import sys
import time

sys.path.insert(0, ".")

from src.client import chat, DEFAULT_MODEL


def test_basic_chat() -> None:
    """测试基础对话连通性"""
    print(f"[测试 1/2] 基础对话 — 模型：{DEFAULT_MODEL}")
    print("-" * 40)

    messages = [{"role": "user", "content": "你好，请用一句话介绍你自己。"}]

    t0 = time.time()
    response = chat(messages)
    elapsed = time.time() - t0

    content = response.choices[0].message.content
    usage = response.usage

    print(f"模型回复：{content}")
    print(f"耗时：{elapsed:.2f}s")
    print(f"Token 用量：prompt={usage.prompt_tokens}，completion={usage.completion_tokens}")
    print()


def test_streaming_chat() -> None:
    """测试流式输出连通性"""
    print(f"[测试 2/2] 流式输出")
    print("-" * 40)

    messages = [{"role": "user", "content": "用三个词描述编程的乐趣。"}]

    print("流式内容：", end="", flush=True)
    stream = chat(messages, stream=True)

    full_text = ""
    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            print(delta, end="", flush=True)
            full_text += delta

    print()
    print(f"流式接收完成，共 {len(full_text)} 字")
    print()


if __name__ == "__main__":
    print("=" * 40)
    print("  千问 API 连通性验证")
    print("=" * 40)
    print()
    try:
        test_basic_chat()
        test_streaming_chat()
        print("✓ 所有测试通过，API 连接正常")
    except Exception as e:
        print(f"✗ 测试失败：{e}")
        sys.exit(1)
