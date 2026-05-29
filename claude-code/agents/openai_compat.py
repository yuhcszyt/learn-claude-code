"""
OpenAI-compatible adapter used by the teaching agents.

The lesson files were originally written around Anthropic's Messages API:
assistant content is a list of text/tool blocks, and tool results are sent
back as ``{"type": "tool_result", ...}``. This module keeps that small
teaching shape, but sends real requests through the OpenAI-compatible
``/v1/chat/completions`` API.
"""

from __future__ import annotations
import logging
import json
import os
from dataclasses import dataclass
from typing import Any

from openai import APIStatusError, OpenAI, OpenAIError

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s"
)

@dataclass
class TextBlock:
    """像 Java 里的简单 POJO：只保存模型返回的一段文本。"""

    text: str
    type: str = "text"


@dataclass
class ToolUseBlock:
    """统一教程内部的工具调用格式，方便旧代码继续用 block.name/block.input。"""

    id: str
    name: str
    input: dict[str, Any]
    type: str = "tool_use"


@dataclass
class MessageResponse:
    """把 OpenAI SDK 的响应压成教程需要的 response.content/stop_reason。"""

    content: list[TextBlock | ToolUseBlock]
    stop_reason: str


class OpenAICompatibleClient:
    """Small wrapper that exposes ``client.messages.create(...)``.

    配置全部来自 .env：
    - OPENAI_API_KEY：密钥
    - OPENAI_BASE_URL：OpenAI 兼容地址，例如 https://api.openai.com/v1
    - OPENAI_MODEL：模型名

    这样每个教程文件只关心“代理循环”，不需要反复写协议转换代码。
    """

    def __init__(self, api_key: str, base_url: str | None, model: str):
        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self._client = OpenAI(**kwargs)
        self.model = model
        self.messages = _Messages(self._client)

    @classmethod
    def from_env(cls) -> "OpenAICompatibleClient":
        """从环境变量创建客户端；load_dotenv 由各教学脚本调用。"""

        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL") or None
        model = os.getenv("OPENAI_MODEL") or os.getenv("MODEL_ID")
        print("Using OpenAI API key: %s", api_key)
        missing = []
        if not api_key:
            missing.append("OPENAI_API_KEY")
        if not model:
            missing.append("OPENAI_MODEL")
        if missing:
            names = ", ".join(missing)
            raise RuntimeError(f"Missing required .env setting(s): {names}")

        return cls(api_key=api_key, base_url=base_url, model=model)


class _Messages:
    """Imitates the tiny subset of Anthropic's ``messages`` client we use."""
    def __init__(self, client: OpenAI):
        self._client = client

    def create(
        self,
        *,
        model: str,
        messages: list[dict[str, Any]],
        system: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> MessageResponse:
        # OpenAI Chat Completions 把 system prompt 放在 messages 第一条。
        openai_messages = []
        if system:
            openai_messages.append({"role": "system", "content": system})
        # logging.info("Internal messages:\n%s", json.dumps(messages, default=str, ensure_ascii=False))
        print("Anthropic message\n:"+json.dumps(messages, indent=2, default=str, ensure_ascii=False))

        openai_messages.extend(_to_openai_messages(messages))

        request: dict[str, Any] = {
            "model": model,
            "messages": openai_messages,
            **kwargs,
        }
        if tools:
            request["tools"] = [_to_openai_tool(tool) for tool in tools]
            request["tool_choice"] = "auto"
        if max_tokens is not None:
            request["max_tokens"] = max_tokens

        try:
            # 打印日志
            # logging.info("OpenAI request:\n%s", json.dumps(request,  default=str, ensure_ascii=False))
            print("openAI:\n"+json.dumps(request,  default=str, ensure_ascii=False))
            response = self._client.chat.completions.create(**request)
        except APIStatusError as e:
            return MessageResponse(content=[TextBlock(text=_format_status_error(e))], stop_reason="api_error")
        except OpenAIError as e:
            return MessageResponse(content=[TextBlock(text=_format_openai_error(e))], stop_reason="api_error")
        choice = response.choices[0]
        message = choice.message

        blocks: list[TextBlock | ToolUseBlock] = []
        if message.content:
            blocks.append(TextBlock(text=message.content))
        for call in message.tool_calls or []:
            blocks.append(
                ToolUseBlock(
                    id=call.id,
                    name=call.function.name,
                    input=_parse_arguments(call.function.arguments),
                )
            )

        # Anthropic 用 tool_use；OpenAI 的 finish_reason 通常是 tool_calls。
        stop_reason = "tool_use" if message.tool_calls else (choice.finish_reason or "end_turn")
        return MessageResponse(content=blocks, stop_reason=stop_reason)


def extract_text(content: Any) -> str:
    """把教程内部的 content 块拼成普通字符串，适合打印或总结。"""

    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return "" if content is None else str(content)

    pieces = []
    for block in content:
        block_type = _get(block, "type")
        if block_type == "text":
            pieces.append(str(_get(block, "text") or ""))
        elif block_type == "tool_use":
            pieces.append(f"[tool_use:{_get(block, 'name')}]")
        else:
            pieces.append(str(block))
    return "\n".join(piece for piece in pieces if piece)


def _to_openai_tool(tool: dict[str, Any]) -> dict[str, Any]:
    """Anthropic 的 input_schema 对应 OpenAI 的 function.parameters。"""

    parameters = tool.get("parameters") or tool.get("input_schema") or {
        "type": "object",
        "properties": {},
    }
    return {
        "type": "function",
        "function": {
            "name": tool["name"],
            "description": tool.get("description", ""),
            "parameters": parameters,
        },
    }


def _to_openai_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """把教程内部消息列表转换成 OpenAI chat messages。

    重点是工具调用：
    assistant 的 tool_use block -> assistant.tool_calls
    user 的 tool_result block -> role=tool 的消息
    """

    converted: list[dict[str, Any]] = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")

        if role == "assistant" and isinstance(content, list):
            converted.append(_assistant_blocks_to_message(content))
            continue

        if role == "user" and isinstance(content, list):
            converted.extend(_user_blocks_to_messages(content))
            continue

        converted.append({"role": role, "content": extract_text(content)})
    return converted


def _assistant_blocks_to_message(blocks: list[Any]) -> dict[str, Any]:
    text_parts = []
    tool_calls = []
    for block in blocks:
        block_type = _get(block, "type")
        if block_type == "text":
            text_parts.append(str(_get(block, "text") or ""))
        elif block_type == "tool_use":
            tool_calls.append(
                {
                    "id": _get(block, "id"),
                    "type": "function",
                    "function": {
                        "name": _get(block, "name"),
                        "arguments": json.dumps(
                            _get(block, "input") or {},
                            ensure_ascii=False,
                        ),
                    },
                }
            )

    message: dict[str, Any] = {
        "role": "assistant",
        "content": "\n".join(text_parts) if text_parts else None,
    }
    if tool_calls:
        message["tool_calls"] = tool_calls
    return message


def _user_blocks_to_messages(blocks: list[Any]) -> list[dict[str, Any]]:
    converted = []
    pending_text = []
    for block in blocks:
        block_type = _get(block, "type")
        if block_type == "tool_result":
            converted.append(
                {
                    "role": "tool",
                    "tool_call_id": _get(block, "tool_use_id"),
                    "content": str(_get(block, "content") or ""),
                }
            )
        elif block_type == "text":
            pending_text.append(str(_get(block, "text") or ""))
        else:
            pending_text.append(str(block))

    if pending_text:
        converted.append({"role": "user", "content": "\n".join(pending_text)})
    return converted


def _parse_arguments(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return {"_raw_arguments": raw}
    return value if isinstance(value, dict) else {"value": value}


def _format_status_error(error: APIStatusError) -> str:
    body = getattr(error, "body", None)
    detail = body.get("error", body) if isinstance(body, dict) else body
    message = detail.get("message") if isinstance(detail, dict) else str(detail or error)
    code = detail.get("code") if isinstance(detail, dict) else None
    request_id = detail.get("request_id") if isinstance(detail, dict) else None

    hint = "请检查 .env 里的 OPENAI_API_KEY、OPENAI_BASE_URL、OPENAI_MODEL，以及服务商账户额度。"
    if "FREE_QUOTA_EXHAUSTED" in message or code == "401008" or error.status_code == 402:
        hint = (
            "当前服务商返回额度耗尽或端点未激活。请到服务商控制台开通/续费额度，"
            "或把 .env 切换到仍可用的 OPENAI_API_KEY、OPENAI_BASE_URL、OPENAI_MODEL。"
        )

    parts = [
        f"OpenAI-compatible API error ({error.status_code})",
        f"message: {message}",
    ]
    if code:
        parts.append(f"code: {code}")
    if request_id:
        parts.append(f"request_id: {request_id}")
    parts.append(hint)
    return "\n".join(parts)


def _format_openai_error(error: OpenAIError) -> str:
    return (
        f"OpenAI-compatible API error: {error}\n"
        "请检查网络连接，以及 .env 里的 OPENAI_API_KEY、OPENAI_BASE_URL、OPENAI_MODEL。"
    )


def _get(obj: Any, key: str) -> Any:
    """同时支持 dataclass/object 属性和 dict 取值。"""

    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)
