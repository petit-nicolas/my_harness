"""
千问 API 客户端封装

通过 OpenAI SDK 兼容模式对接阿里云千问，
对外暴露统一的 chat() 接口，屏蔽底层细节。
"""
import os
from typing import Iterator
from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionChunk
from dotenv import load_dotenv

from src.retry import with_retry

# 加载 .ENV 文件中的环境变量
load_dotenv(dotenv_path=".ENV")

# 千问兼容 OpenAI 协议的 endpoint
_QWEN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

# 默认模型：qwen-plus 性价比高，qwen-max 能力更强
DEFAULT_MODEL = "qwen-plus"


def _make_client() -> OpenAI:
    """创建并返回 OpenAI 客户端（指向千问 endpoint）"""
    api_key = os.environ.get("Ali_API_KEY")
    if not api_key:
        raise ValueError(
            "未找到 Ali_API_KEY，请确认 .ENV 文件存在且包含该变量"
        )
    return OpenAI(api_key=api_key, base_url=_QWEN_BASE_URL)


# 模块级单例，避免重复创建
_client: OpenAI | None = None


def get_client() -> OpenAI:
    """获取全局客户端单例"""
    global _client
    if _client is None:
        _client = _make_client()
    return _client


def chat(
    messages: list[ChatCompletionMessageParam],
    model: str = DEFAULT_MODEL,
    tools: list[dict] | None = None,
    stream: bool = False,
) -> ChatCompletionChunk | Iterator[ChatCompletionChunk]:
    """
    发送对话请求到千问 API。

    Args:
        messages: 消息历史列表，格式同 OpenAI Chat API
        model:    模型名称，默认 qwen-plus
        tools:    工具定义列表（JSON Schema），用于 function calling
        stream:   是否启用流式输出

    Returns:
        stream=False 时返回完整 ChatCompletion 对象；
        stream=True  时返回 chunk 迭代器
    """
    client = get_client()

    kwargs: dict = {
        "model": model,
        "messages": messages,
        "stream": stream,
    }
    if tools:
        kwargs["tools"] = tools

    # 流式请求不重试（迭代器无法重放），非流式自动重试 3 次
    if stream:
        return client.chat.completions.create(**kwargs)

    return with_retry(lambda: client.chat.completions.create(**kwargs))
