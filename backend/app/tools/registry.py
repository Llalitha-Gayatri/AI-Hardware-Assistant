"""Strict tool registry, allowlist, and execution dispatcher for AI tool calling."""
from typing import Any, Callable, Dict, List, Optional
from app.schemas.chat import ToolExecutionResult
from app.tools.cpu import inspect_cpu
from app.tools.environment import detect_environment
from app.tools.gpu import inspect_gpu
from app.tools.motherboard import inspect_memory_slots, inspect_motherboard
from app.tools.ram import inspect_ram
from app.tools.storage import inspect_storage


class ToolDefinition:
    """Represents a strictly registered hardware inspection tool."""

    def __init__(
        self,
        name: str,
        display_name: str,
        description: str,
        func: Callable[[], Any],
    ):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.func = func

    def to_openai_schema(self) -> Dict[str, Any]:
        """Convert tool to OpenAI standard tool calling schema format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
        }


# Strict allowlist of permitted tools
_REGISTRY: Dict[str, ToolDefinition] = {
    "inspect_cpu": ToolDefinition(
        name="inspect_cpu",
        display_name="CPU Inspector",
        description="Inspect processor details including CPU model, architecture, core count, thread count, clock speeds, and hardware virtualization support.",
        func=inspect_cpu,
    ),
    "inspect_ram": ToolDefinition(
        name="inspect_ram",
        display_name="RAM Inspector",
        description="Inspect system memory (RAM) usage, total capacity, currently used memory, and available memory.",
        func=inspect_ram,
    ),
    "inspect_gpu": ToolDefinition(
        name="inspect_gpu",
        display_name="GPU Inspector",
        description="Inspect graphics cards and GPU controllers, PCI IDs, and vendor/model names.",
        func=inspect_gpu,
    ),
    "inspect_storage": ToolDefinition(
        name="inspect_storage",
        display_name="Storage Inspector",
        description="Inspect storage drives, partitions, mountpoints, filesystems, and verified media types (NVMe SSD, SATA SSD, HDD).",
        func=inspect_storage,
    ),
    "inspect_motherboard": ToolDefinition(
        name="inspect_motherboard",
        display_name="Motherboard & BIOS Inspector",
        description="Inspect motherboard manufacturer, board model, and BIOS version and release date.",
        func=inspect_motherboard,
    ),
    "inspect_memory_slots": ToolDefinition(
        name="inspect_memory_slots",
        display_name="Memory Slots & Upgrade Inspector",
        description="Inspect physical RAM slots, occupied slots, installed module specifications, and maximum supported memory capacity.",
        func=inspect_memory_slots,
    ),
    "inspect_environment": ToolDefinition(
        name="inspect_environment",
        display_name="System & WSL2 Environment Inspector",
        description="Inspect Linux distribution, kernel version, and detect whether the host is running under WSL2 with hypervisor virtualization constraints.",
        func=detect_environment,
    ),
}


def get_available_tools_schema() -> List[Dict[str, Any]]:
    """Return all tool schemas for LLM prompts."""
    return [tool.to_openai_schema() for tool in _REGISTRY.values()]


def is_tool_allowed(tool_name: str) -> bool:
    """Validate if requested tool name is in the strict allowlist."""
    return tool_name in _REGISTRY


def execute_tool(tool_name: str) -> ToolExecutionResult:
    """
    Validate and execute a strictly allowlisted hardware inspection tool.
    
    Security:
    - Rejects any tool not explicitly in _REGISTRY.
    - Captures exceptions to guarantee safe, controlled error returns.
    """
    if not is_tool_allowed(tool_name):
        return ToolExecutionResult(
            tool_name=tool_name,
            display_name=tool_name,
            success=False,
            error=f"Security violation: Tool '{tool_name}' is not in the allowlist of inspection tools.",
        )

    tool_def = _REGISTRY[tool_name]
    try:
        raw_result = tool_def.func()
        # Convert Pydantic models or dicts to json-compatible dict
        if hasattr(raw_result, "model_dump"):
            data = raw_result.model_dump()
        elif hasattr(raw_result, "dict"):
            data = raw_result.dict()
        elif isinstance(raw_result, dict):
            data = raw_result
        else:
            data = {"result": str(raw_result)}

        return ToolExecutionResult(
            tool_name=tool_name,
            display_name=tool_def.display_name,
            success=True,
            data=data,
            error=None,
        )

    except Exception as exc:
        return ToolExecutionResult(
            tool_name=tool_name,
            display_name=tool_def.display_name,
            success=False,
            error=f"Error executing tool '{tool_name}': {str(exc)}",
        )
