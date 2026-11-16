"""Pydantic schemas for chat interactions and tool-calling workflow."""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """Message object for multi-turn conversation history."""
    role: str = Field(..., description="Role: 'user', 'assistant', 'system', or 'tool'")
    content: str = Field("", description="Text content of the message")
    name: Optional[str] = Field(None, description="Tool name if role is 'tool'")
    tool_call_id: Optional[str] = Field(None, description="Matching tool call identifier")
    tool_calls: Optional[List[Dict[str, Any]]] = Field(
        None, description="Tool calls issued by assistant"
    )


class ChatRequest(BaseModel):
    """Incoming user chat query."""
    message: str = Field(..., min_length=1, description="Natural language question")
    history: List[ChatMessage] = Field(
        default_factory=list, description="Previous messages in this session"
    )


class ToolExecutionResult(BaseModel):
    """Result of a backend tool execution dispatched by the LLM."""
    tool_name: str
    display_name: str
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class ChatResponse(BaseModel):
    """Chatbot response with grounded answer and tool traceability."""
    answer: str
    tools_used: List[str] = Field(default_factory=list)
    tool_results: List[ToolExecutionResult] = Field(default_factory=list)
    is_mock: bool = False
    warning: Optional[str] = None
