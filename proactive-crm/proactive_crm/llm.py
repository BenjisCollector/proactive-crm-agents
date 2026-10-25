"""Chat client selection. Live: an OpenAI-compatible or Azure OpenAI endpoint via Microsoft Agent Framework. Demo: canned outputs."""
import os
from collections.abc import Awaitable, Mapping, Sequence
from typing import Any, ClassVar

from agent_framework import BaseChatClient, ChatMiddlewareLayer, ChatResponse, FunctionInvocationLayer, Message
from agent_framework.observability import ChatTelemetryLayer

from . import canned


class _Raw(BaseChatClient):
    """A real Agent Framework chat client whose 'model' is the deterministic templates in canned.py."""

    OTEL_PROVIDER_NAME: ClassVar[str] = "canned-demo"

    def _inner_get_response(self, *, messages: Sequence[Message], stream: bool, options: Mapping[str, Any], **kwargs: Any) -> Awaitable[ChatResponse]:
        if stream:
            raise NotImplementedError("demo client does not stream")
        prompt = next(m.text for m in reversed(messages) if m.role == "user")

        async def _go() -> ChatResponse:
            return ChatResponse(messages=[Message(role="assistant", contents=[canned.answer(prompt)])], model="canned-demo")

        return _go()


class CannedChatClient(FunctionInvocationLayer, ChatMiddlewareLayer, ChatTelemetryLayer, _Raw):
    OTEL_PROVIDER_NAME: ClassVar[str] = "canned-demo"


def mode() -> dict:
    """Env var NAMES only are inspected here; values are never logged or returned."""
    if os.environ.get("CRM_FORCE_DEMO") == "1":
        return {"mode": "demo", "provider": None, "model": "canned"}
    if os.environ.get("OPENAI_API_KEY"):
        return {"mode": "live", "provider": "openai-compatible", "model": os.environ.get("OPENAI_MODEL", "gpt-4o-mini")}
    if os.environ.get("AZURE_OPENAI_ENDPOINT") and os.environ.get("AZURE_OPENAI_API_KEY"):
        return {"mode": "live", "provider": "azure-openai", "model": os.environ.get("AZURE_OPENAI_MODEL") or os.environ.get("AZURE_OPENAI_CHAT_COMPLETION_MODEL", "")}
    return {"mode": "demo", "provider": None, "model": "canned"}


def make_client():
    m = mode()
    if m["mode"] == "demo":
        return CannedChatClient()
    from agent_framework_openai import OpenAIChatCompletionClient  # reads OPENAI_* or AZURE_OPENAI_* itself

    return OpenAIChatCompletionClient(model=m["model"] or None)
