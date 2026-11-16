"""LLM Client abstraction supporting OpenAI, compatible providers, and a Mock provider."""
import json
import re
import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import httpx
from app.config import settings


class LLMToolCall:
    """Standardized representation of a tool call requested by the LLM."""

    def __init__(self, call_id: str, function_name: str, arguments: Dict[str, Any]):
        self.id = call_id
        self.name = function_name
        self.arguments = arguments

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": "function",
            "function": {
                "name": self.name,
                "arguments": json.dumps(self.arguments),
            },
        }


class LLMResponse:
    """Standardized response from an LLM invocation."""

    def __init__(
        self,
        content: Optional[str] = None,
        tool_calls: Optional[List[LLMToolCall]] = None,
        is_mock: bool = False,
    ):
        self.content = content
        self.tool_calls = tool_calls or []
        self.is_mock = is_mock

    @property
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0


class BaseLLMClient(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> LLMResponse:
        """Submit conversation and tools, returning LLMResponse."""
        pass


class OpenAICompatibleClient(BaseLLMClient):
    """Client for OpenAI and any OpenAI-compatible API (Groq, vLLM, Ollama, etc.)."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o-mini",
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> LLMResponse:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.2,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            if resp.status_code != 200:
                raise RuntimeError(
                    f"LLM API error ({resp.status_code}): {resp.text}"
                )

            data = resp.json()
            choice = data["choices"][0]["message"]
            content = choice.get("content")
            raw_calls = choice.get("tool_calls") or []

            parsed_tool_calls: List[LLMToolCall] = []
            for tc in raw_calls:
                call_id = tc.get("id", str(uuid.uuid4()))
                fn = tc.get("function", {})
                fn_name = fn.get("name", "")
                raw_args = fn.get("arguments", "{}")
                try:
                    args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                except Exception:
                    args = {}
                parsed_tool_calls.append(
                    LLMToolCall(call_id=call_id, function_name=fn_name, arguments=args)
                )

            return LLMResponse(
                content=content,
                tool_calls=parsed_tool_calls,
                is_mock=False,
            )


class MockLLMClient(BaseLLMClient):
    """
    Deterministic Mock LLM client for offline development and testing.
    
    Adheres strictly to requirement:
    - Never pretends to be genuine AI.
    - Demonstrates full tool-calling execution cycle.
    - Accurately generates grounded responses from tool data.
    """

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> LLMResponse:
        # Check if the last messages are tool results
        tool_messages = [m for m in messages if m.get("role") == "tool"]
        
        # If tool results exist in recent turns, generate a grounded synthesis response
        if tool_messages and messages[-1].get("role") == "tool":
            return self._synthesize_grounded_answer(tool_messages, messages)

        # Otherwise, analyze the user's latest message to emit appropriate tool calls
        user_msg = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                user_msg = m.get("content", "").lower()
                break

        requested_tools: List[LLMToolCall] = []

        # Intent: RAM Upgrade / Slots
        if any(w in user_msg for w in ["upgrade", "expand", "max ram", "slots", "dimm"]):
            requested_tools.append(
                LLMToolCall(str(uuid.uuid4()), "inspect_ram", {})
            )
            requested_tools.append(
                LLMToolCall(str(uuid.uuid4()), "inspect_memory_slots", {})
            )
        # Intent: RAM capacity / usage
        elif any(w in user_msg for w in ["ram", "memory"]):
            requested_tools.append(
                LLMToolCall(str(uuid.uuid4()), "inspect_ram", {})
            )
        # Intent: CPU / Processor
        if any(w in user_msg for w in ["cpu", "processor", "core", "frequency", "clock", "threads"]):
            requested_tools.append(
                LLMToolCall(str(uuid.uuid4()), "inspect_cpu", {})
            )
        # Intent: GPU / Graphics
        if any(w in user_msg for w in ["gpu", "graphic", "display", "video card", "vga", "nvidia", "radeon", "intel arc"]):
            requested_tools.append(
                LLMToolCall(str(uuid.uuid4()), "inspect_gpu", {})
            )
        # Intent: Storage / SSD / NVMe / HDD / Disk
        if any(w in user_msg for w in ["storage", "disk", "ssd", "nvme", "sata", "hdd", "space", "hard drive", "capacity"]):
            requested_tools.append(
                LLMToolCall(str(uuid.uuid4()), "inspect_storage", {})
            )
        # Intent: Motherboard / BIOS
        if any(w in user_msg for w in ["motherboard", "bios", "mainboard", "vendor", "manufacturer"]):
            requested_tools.append(
                LLMToolCall(str(uuid.uuid4()), "inspect_motherboard", {})
            )
        # Intent: Environment / WSL2
        if any(w in user_msg for w in ["wsl", "linux", "distro", "kernel", "os", "operating system"]):
            requested_tools.append(
                LLMToolCall(str(uuid.uuid4()), "inspect_environment", {})
            )

        # Fallback for general hardware questions
        if not requested_tools and any(w in user_msg for w in ["specs", "hardware", "system info", "computer", "pc", "laptop"]):
            requested_tools = [
                LLMToolCall(str(uuid.uuid4()), "inspect_cpu", {}),
                LLMToolCall(str(uuid.uuid4()), "inspect_ram", {}),
                LLMToolCall(str(uuid.uuid4()), "inspect_gpu", {}),
                LLMToolCall(str(uuid.uuid4()), "inspect_storage", {}),
            ]

        # Handle follow-up questions that don't need new tools (e.g. "Is it good for machine learning?")
        if not requested_tools:
            # Check if previous conversation history has relevant data
            return self._handle_conversational_followup(user_msg, messages)

        return LLMResponse(
            content=None,
            tool_calls=requested_tools,
            is_mock=True,
        )

    def _handle_conversational_followup(
        self, user_msg: str, messages: List[Dict[str, Any]]
    ) -> LLMResponse:
        """Handle questions evaluating previously inspected hardware (e.g. gaming, ML)."""
        history_text = json.dumps(messages)
        
        if "machine learning" in user_msg or "ml" in user_msg or "deep learning" in user_msg or "ai" in user_msg:
            # Look for GPU in history
            if "gpu" in history_text.lower() or "nvidia" in history_text.lower():
                return LLMResponse(
                    content=(
                        "**[Mock LLM Mode: Configurable in .env]**\n\n"
                        "Based on your previously detected GPU:\n"
                        "- If your system features a dedicated NVIDIA GPU (e.g., RTX series), it provides CUDA support, "
                        "making it suitable for running local PyTorch models, small LLMs (with quantization like GGUF/AWQ), "
                        "and classical machine learning workflows.\n"
                        "- If your system only uses integrated Intel/AMD graphics, ML training will be limited, "
                        "though lightweight CPU inference (via ONNX or llama.cpp) remains feasible.\n\n"
                        "*Note: Hardware suitability is evaluated based on verified device specifications.*"
                    ),
                    is_mock=True,
                )
            else:
                # Trigger GPU tool to check first
                return LLMResponse(
                    tool_calls=[LLMToolCall(str(uuid.uuid4()), "inspect_gpu", {})],
                    is_mock=True,
                )

        if "game" in user_msg or "gaming" in user_msg:
            return LLMResponse(
                content=(
                    "**[Mock LLM Mode: Configurable in .env]**\n\n"
                    "Gaming capability relies primarily on your dedicated GPU and thermal capacity. "
                    "Ensure your graphics drivers are up to date via your Linux package manager (e.g., nvidia-driver or mesa)."
                ),
                is_mock=True,
            )

        # Default conversational answer
        return LLMResponse(
            content=(
                "**[Mock LLM Mode: Configurable in .env]**\n\n"
                "I am your Linux Hardware Assistant. You can ask me questions like:\n"
                "- *How much RAM do I have?*\n"
                "- *Which processor does my laptop use?*\n"
                "- *What GPU do I have?*\n"
                "- *Is my SSD NVMe or SATA?*\n"
                "- *How much storage is available?*\n"
                "- *Can I upgrade my RAM?*"
            ),
            is_mock=True,
        )

    def _synthesize_grounded_answer(
        self,
        tool_messages: List[Dict[str, Any]],
        all_messages: List[Dict[str, Any]],
    ) -> LLMResponse:
        """Synthesize a verified, grounded answer from executed tool outputs."""
        results_by_name: Dict[str, Any] = {}
        for tm in tool_messages:
            name = tm.get("name")
            try:
                results_by_name[name] = json.loads(tm.get("content", "{}"))
            except Exception:
                results_by_name[name] = {}

        sections = ["**[Mock LLM Mode: Configurable in .env]**\n"]

        # CPU synthesis
        if "inspect_cpu" in results_by_name:
            cpu = results_by_name["inspect_cpu"]
            if cpu.get("error"):
                sections.append(f"**CPU**: Could not determine CPU details ({cpu['error']}).")
            else:
                model = cpu.get("model", "Unknown")
                arch = cpu.get("architecture", "Unknown")
                cores = cpu.get("cores")
                threads = cpu.get("threads")
                freq = cpu.get("max_frequency_mhz") or cpu.get("frequency_mhz")
                virt = cpu.get("virtualization")
                
                txt = f"**Processor**: {model}\n"
                txt += f"- **Architecture**: {arch}\n"
                txt += f"- **Cores / Threads**: {cores or 'N/A'} cores, {threads or 'N/A'} threads\n"
                if freq:
                    txt += f"- **Clock Speed**: {freq} MHz\n"
                if virt:
                    txt += f"- **Virtualization**: {virt}\n"
                sections.append(txt)

        # RAM synthesis
        if "inspect_ram" in results_by_name:
            ram = results_by_name["inspect_ram"]
            if ram.get("error"):
                sections.append(f"**RAM**: Could not inspect memory ({ram['error']}).")
            else:
                tot = ram.get("total_human", "N/A")
                used = ram.get("used_human", "N/A")
                avail = ram.get("available_human", "N/A")
                pct = ram.get("usage_percentage", "N/A")
                sections.append(
                    f"**System Memory (RAM)**:\n"
                    f"- **Total**: {tot}\n"
                    f"- **Available**: {avail}\n"
                    f"- **In Use**: {used} ({pct}%)\n"
                )

        # Memory Slots & Upgrade synthesis
        if "inspect_memory_slots" in results_by_name:
            slots_data = results_by_name["inspect_memory_slots"]
            if slots_data.get("permission_denied"):
                sections.append(
                    "**Memory Slots & Upgrade Status**:\n"
                    "- *Permission Notice*: Reading physical motherboard memory slots requires root/sudo permissions (via dmidecode). "
                    "Cannot verify free slots or maximum motherboard capacity without elevated permissions."
                )
            elif slots_data.get("error"):
                sections.append(f"**Memory Slots & Upgrade Status**: {slots_data['error']}")
            else:
                tot_slots = slots_data.get("total_slots")
                occ_slots = slots_data.get("occupied_slots")
                max_cap = slots_data.get("max_capacity_human")
                txt = "**Memory Slots & Upgrade Status**:\n"
                txt += f"- **Total Slots**: {tot_slots if tot_slots is not None else 'Could not be determined'}\n"
                txt += f"- **Occupied Slots**: {occ_slots if occ_slots is not None else 'N/A'}\n"
                txt += f"- **Maximum Supported Capacity**: {max_cap if max_cap else 'Not reported by motherboard DMI table'}\n"
                
                # Upgrade recommendation grounded in verified numbers
                if tot_slots and occ_slots is not None:
                    free_slots = tot_slots - occ_slots
                    if free_slots > 0:
                        txt += f"- **Upgrade Assessment**: You have {free_slots} free memory slot(s) available for expansion."
                    else:
                        txt += "- **Upgrade Assessment**: All physical memory slots are currently populated. Upgrading would require replacing existing module(s)."
                sections.append(txt)

        # GPU synthesis
        if "inspect_gpu" in results_by_name:
            gpu = results_by_name["inspect_gpu"]
            if gpu.get("error"):
                sections.append(f"**GPU**: {gpu['error']}")
            else:
                devices = gpu.get("devices", [])
                if not devices:
                    sections.append("**GPU**: No dedicated or integrated PCI graphics controllers detected.")
                else:
                    txt = f"**Graphics Controllers ({len(devices)} detected)**:\n"
                    for idx, dev in enumerate(devices, 1):
                        txt += f"{idx}. **{dev.get('vendor', 'Unknown')}** - {dev.get('model', 'Unknown')} (`{dev.get('controller_type', 'VGA')}`)\n"
                    sections.append(txt)

        # Storage synthesis
        if "inspect_storage" in results_by_name:
            st = results_by_name["inspect_storage"]
            if st.get("error"):
                sections.append(f"**Storage**: {st['error']}")
            else:
                devs = st.get("devices", [])
                disks = [d for d in devs if d.get("device_type") == "disk"]
                txt = f"**Storage Devices ({len(disks)} physical drive(s))**:\n"
                for d in disks:
                    m_type = d.get("media_type", "Unknown")
                    txt += f"- **{d.get('name')}**: {d.get('size_human', 'N/A')} - **Type**: {m_type}"
                    if d.get("model"):
                        txt += f" ({d['model']})"
                    if d.get("mountpoint"):
                        txt += f" mounted at `{d['mountpoint']}`"
                    txt += "\n"
                sections.append(txt)

        # Motherboard synthesis
        if "inspect_motherboard" in results_by_name:
            mb = results_by_name["inspect_motherboard"]
            txt = "**Motherboard & BIOS**:\n"
            if mb.get("manufacturer") or mb.get("product_name"):
                txt += f"- **Manufacturer**: {mb.get('manufacturer', 'Unknown')}\n"
                txt += f"- **Model**: {mb.get('product_name', 'Unknown')}\n"
            if mb.get("bios_version"):
                txt += f"- **BIOS Version**: {mb.get('bios_version')} ({mb.get('bios_date', 'Unknown date')})\n"
            if mb.get("permission_denied"):
                txt += "- *Notice*: dmidecode requires root privileges; fallback values obtained via sysfs.\n"
            sections.append(txt)

        # Environment synthesis
        if "inspect_environment" in results_by_name:
            env = results_by_name["inspect_environment"]
            txt = f"**System Environment**: {env.get('distro_name', 'Linux')}\n"
            if env.get("is_wsl2"):
                txt += f"- **WSL2 Detected**: {env.get('warning')}\n"
            sections.append(txt)

        return LLMResponse(content="\n\n".join(sections), is_mock=True)


def get_llm_client() -> BaseLLMClient:
    """Factory creating the appropriate LLM client based on configuration."""
    provider = settings.LLM_PROVIDER.lower()

    if provider == "openai":
        if not settings.OPENAI_API_KEY:
            # Fallback to mock if API key is missing
            return MockLLMClient()
        return OpenAICompatibleClient(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
            model=settings.OPENAI_MODEL,
        )

    elif provider == "gemini":
        if not settings.GEMINI_API_KEY:
            return MockLLMClient()
        # Google Gemini supports OpenAI-compatible endpoint
        return OpenAICompatibleClient(
            api_key=settings.GEMINI_API_KEY,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai",
            model=settings.GEMINI_MODEL,
        )

    # Default to Mock provider for development and testing
    return MockLLMClient()
