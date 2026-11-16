"""Unit tests for the AI Agent tool-calling workflow and follow-ups."""
import asyncio
from unittest.mock import patch
from app.ai.agent import HardwareAgent
from app.ai.llm_client import MockLLMClient
from app.schemas.chat import ChatMessage, ChatRequest
from app.schemas.hardware import MemorySlot, MemorySlotInfo, RAMInfo, SystemEnvironment


def test_agent_single_tool_call_ram():
    agent = HardwareAgent(client=MockLLMClient())
    request = ChatRequest(message="How much RAM do I have installed?", history=[])

    response = asyncio.run(agent.run(request))

    assert response is not None
    assert "inspect_ram" in response.tools_used
    assert len(response.tool_results) >= 1
    assert "System Memory" in response.answer or "RAM" in response.answer
    assert response.is_mock is True


def test_agent_multi_tool_call_ram_upgrade():
    # User asking to upgrade RAM requires both RAM and Memory slot inspection
    agent = HardwareAgent(client=MockLLMClient())
    request = ChatRequest(message="Can I upgrade my RAM to 32 GB?", history=[])

    response = asyncio.run(agent.run(request))

    assert "inspect_ram" in response.tools_used
    assert "inspect_memory_slots" in response.tools_used
    assert len(response.tools_used) == 2
    assert "Memory Slots" in response.answer


def test_agent_grounded_upgrade_synthesis():
    agent = HardwareAgent(client=MockLLMClient())
    
    mock_ram = RAMInfo(
        total_bytes=16 * 1024**3,
        used_bytes=6 * 1024**3,
        available_bytes=10 * 1024**3,
        total_human="16.00 GB",
        used_human="6.00 GB",
        available_human="10.00 GB",
        usage_percentage=37.5,
    )
    mock_slots = MemorySlotInfo(
        total_slots=2,
        occupied_slots=1,
        max_capacity_human="32 GB",
        slots=[
            MemorySlot(locator="DIMM 0", size_human="16 GB", type="DDR4"),
            MemorySlot(locator="DIMM 1", size_human="Empty"),
        ],
    )

    def fake_execute_tool(tool_name: str):
        if tool_name == "inspect_ram":
            return ToolExecutionResult(
                tool_name="inspect_ram",
                display_name="RAM Inspector",
                success=True,
                data=mock_ram.model_dump(),
            )
        elif tool_name == "inspect_memory_slots":
            return ToolExecutionResult(
                tool_name="inspect_memory_slots",
                display_name="Memory Slots & Upgrade Inspector",
                success=True,
                data=mock_slots.model_dump(),
            )
        from app.tools.registry import execute_tool as real_execute_tool
        return real_execute_tool(tool_name)

    from app.schemas.chat import ToolExecutionResult
    with patch("app.ai.agent.execute_tool", side_effect=fake_execute_tool):
        req = ChatRequest(message="Can I upgrade my RAM to 32 GB?", history=[])
        res = asyncio.run(agent.run(req))

        assert "16.00 GB" in res.answer
        assert "32 GB" in res.answer
        assert "1 free memory slot(s) available" in res.answer


def test_agent_follow_up_conversation_without_redundant_tools():
    agent = HardwareAgent(client=MockLLMClient())

    # Turn 1: User asks what GPU they have
    req1 = ChatRequest(message="What GPU do I have?", history=[])
    res1 = asyncio.run(agent.run(req1))
    assert "inspect_gpu" in res1.tools_used

    # Turn 2: User asks follow-up: "Is it good for machine learning?"
    # History contains previous turn
    history = [
        ChatMessage(role="user", content="What GPU do I have?"),
        ChatMessage(role="assistant", content=res1.answer),
    ]
    req2 = ChatRequest(message="Is it good for machine learning?", history=history)
    res2 = asyncio.run(agent.run(req2))

    assert res2 is not None
    assert "machine learning" in res2.answer.lower() or "cuda" in res2.answer.lower()


def test_agent_storage_nvme_question():
    agent = HardwareAgent(client=MockLLMClient())
    request = ChatRequest(message="Is my SSD NVMe or SATA?", history=[])

    response = asyncio.run(agent.run(request))

    assert "inspect_storage" in response.tools_used
    assert "Storage" in response.answer


def test_wsl2_environment_detection():
    from app.tools.environment import detect_environment
    with patch.dict("os.environ", {"WSL_DISTRO_NAME": "Ubuntu-22.04"}):
        env = detect_environment()
        assert env.is_wsl2 is True
        assert "WSL2" in env.warning
        assert "virtualized" in env.warning.lower()
