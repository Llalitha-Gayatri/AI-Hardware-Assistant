"""AI Agent orchestrating LLM tool calling, validation, and multi-turn execution."""
import json
from typing import Any, Dict, List, Set
from app.ai.llm_client import BaseLLMClient, get_llm_client
from app.ai.prompts import SYSTEM_PROMPT
from app.schemas.chat import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ToolExecutionResult,
)
from app.tools.registry import (
    execute_tool,
    get_available_tools_schema,
    is_tool_allowed,
)


class HardwareAgent:
    """Orchestrates hardware Q&A reasoning and tool execution loop."""

    def __init__(self, client: BaseLLMClient = None):
        self._client = client
        self.max_tool_rounds = 4

    @property
    def client(self) -> BaseLLMClient:
        return self._client if self._client is not None else get_llm_client()

    async def run(self, request: ChatRequest) -> ChatResponse:
        """
        Execute full conversational agent workflow.
        
        Steps:
        1. Assemble conversation history with system instructions.
        2. Query LLM with available hardware inspection tools.
        3. If LLM requests tool(s), validate against security allowlist.
        4. Execute allowlisted tools, collect structured JSON outputs.
        5. Feed results back into conversation.
        6. Produce final grounded natural-language answer.
        """
        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]

        # Append previous conversation history
        for msg in request.history:
            msg_dict: Dict[str, Any] = {"role": msg.role, "content": msg.content}
            if msg.name:
                msg_dict["name"] = msg.name
            if msg.tool_call_id:
                msg_dict["tool_call_id"] = msg.tool_call_id
            if msg.tool_calls:
                msg_dict["tool_calls"] = msg.tool_calls
            messages.append(msg_dict)

        # Append current user prompt
        messages.append({"role": "user", "content": request.message})

        tools_schema = get_available_tools_schema()
        tools_used_set: Set[str] = set()
        tool_results_list: List[ToolExecutionResult] = []
        is_mock_run = False

        for round_idx in range(self.max_tool_rounds):
            try:
                response = await self.client.chat(messages, tools=tools_schema)
            except Exception as e:
                return ChatResponse(
                    answer=f"An error occurred while communicating with the AI service: {str(e)}",
                    tools_used=list(tools_used_set),
                    tool_results=tool_results_list,
                    is_mock=is_mock_run,
                )

            is_mock_run = is_mock_run or response.is_mock

            # If no tool calls were requested, we have our final synthesized answer
            if not response.has_tool_calls:
                answer = response.content or "No response was generated."
                return ChatResponse(
                    answer=answer,
                    tools_used=list(tools_used_set),
                    tool_results=tool_results_list,
                    is_mock=is_mock_run,
                )

            # LLM requested one or more tool calls: validate and execute each
            assistant_tool_calls_payload = []
            for tool_call in response.tool_calls:
                assistant_tool_calls_payload.append(tool_call.to_dict())

            # Add assistant's tool-call request to messages
            messages.append({
                "role": "assistant",
                "content": "",
                "tool_calls": assistant_tool_calls_payload,
            })

            for tool_call in response.tool_calls:
                fn_name = tool_call.name
                call_id = tool_call.id
                tools_used_set.add(fn_name)

                # Strict security validation
                if not is_tool_allowed(fn_name):
                    res = ToolExecutionResult(
                        tool_name=fn_name,
                        display_name=fn_name,
                        success=False,
                        error=f"Security violation: tool '{fn_name}' rejected.",
                    )
                else:
                    res = execute_tool(fn_name)

                tool_results_list.append(res)

                # Pass tool output back into dialogue context
                tool_output_str = json.dumps(res.data if res.success else {"error": res.error})
                messages.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "name": fn_name,
                    "content": tool_output_str,
                })

        # If loop reached max rounds without finishing
        return ChatResponse(
            answer="Exceeded maximum tool calling iterations. Please simplify your query.",
            tools_used=list(tools_used_set),
            tool_results=tool_results_list,
            is_mock=is_mock_run,
        )


hardware_agent = HardwareAgent()
