"""Unit tests verifying real LLM client integration and OpenAI tool-calling protocol."""
import asyncio
import json
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
import pytest
from app.ai.agent import HardwareAgent
from app.ai.llm_client import (
    OpenAICompatibleClient,
    get_llm_client,
    LLMToolCall,
)
from app.config import settings
from app.schemas.chat import ChatRequest


def test_get_llm_client_returns_openai_when_configured():
    with patch.object(settings, "LLM_PROVIDER", "openai"), \
         patch.object(settings, "OPENAI_API_KEY", "sk-test-fake-key-12345"), \
         patch.object(settings, "OPENAI_BASE_URL", "https://api.openai.com/v1"), \
         patch.object(settings, "OPENAI_MODEL", "gpt-4o-mini"):
        client = get_llm_client()
        assert isinstance(client, OpenAICompatibleClient)
        assert client.api_key == "sk-test-fake-key-12345"
        assert client.model == "gpt-4o-mini"
        assert client.base_url == "https://api.openai.com/v1"


def test_get_llm_client_falls_back_to_mock_when_key_empty():
    from app.ai.llm_client import MockLLMClient
    with patch.object(settings, "LLM_PROVIDER", "openai"), \
         patch.object(settings, "OPENAI_API_KEY", ""):
        client = get_llm_client()
        assert isinstance(client, MockLLMClient)


def test_real_llm_tool_calling_workflow_with_openai_client():
    """
    Verify complete tool-calling lifecycle with OpenAICompatibleClient:
    1. First round: LLM responds with tool_calls requesting 'inspect_cpu'.
    2. Agent executes 'inspect_cpu' and feeds result back as a role='tool' message.
    3. Second round: LLM responds with final synthesized answer.
    """
    openai_client = OpenAICompatibleClient(
        api_key="sk-real-test-key",
        base_url="https://api.openai.com/v1",
        model="gpt-4o-mini",
    )

    # Synthetic OpenAI responses for round 1 (tool call) and round 2 (final answer)
    response_round_1 = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_abc123",
                            "type": "function",
                            "function": {
                                "name": "inspect_cpu",
                                "arguments": "{}",
                            },
                        }
                    ],
                }
            }
        ]
    }

    response_round_2 = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "Your system is powered by an Intel Core i7-12700H processor with 14 cores and 20 threads.",
                    "tool_calls": None,
                }
            }
        ]
    }

    mock_resp1 = MagicMock()
    mock_resp1.status_code = 200
    mock_resp1.json.return_value = response_round_1

    mock_resp2 = MagicMock()
    mock_resp2.status_code = 200
    mock_resp2.json.return_value = response_round_2

    post_calls = []

    async def mock_post(*args, **kwargs):
        post_calls.append((args, kwargs))
        if len(post_calls) == 1:
            return mock_resp1
        return mock_resp2

    with patch("httpx.AsyncClient.post", side_effect=mock_post):
        agent = HardwareAgent(client=openai_client)
        req = ChatRequest(message="Which processor does my laptop use?", history=[])
        res = asyncio.run(agent.run(req))

        # Verification
        assert res.is_mock is False
        assert "inspect_cpu" in res.tools_used
        assert len(res.tool_results) == 1
        assert res.tool_results[0].tool_name == "inspect_cpu"
        assert "Intel Core i7-12700H" in res.answer

        # Verify that 2 HTTP calls were made to OpenAI
        assert len(post_calls) == 2

        # Verify request 1 sent available tools
        call1_kwargs = post_calls[0][1]
        assert "tools" in call1_kwargs["json"]
        assert any(t["function"]["name"] == "inspect_cpu" for t in call1_kwargs["json"]["tools"])
        assert call1_kwargs["headers"]["Authorization"] == "Bearer sk-real-test-key"

        # Verify request 2 included the tool execution output
        call2_kwargs = post_calls[1][1]
        sent_messages = call2_kwargs["json"]["messages"]
        tool_msg = next((m for m in sent_messages if m.get("role") == "tool"), None)
        assert tool_msg is not None
        assert tool_msg["tool_call_id"] == "call_abc123"
        assert tool_msg["name"] == "inspect_cpu"
        # Content is the JSON string from inspect_cpu
        tool_data = json.loads(tool_msg["content"])
        assert "model" in tool_data
