"""
Framework fingerprint signatures.
Each signature defines how to identify a known AI pipeline framework.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class FrameworkType(str, Enum):
    langchain  = "langchain"
    autogen    = "autogen"
    n8n        = "n8n"
    crewai     = "crewai"
    llamaindex = "llamaindex"
    dify       = "dify"
    flowise    = "flowise"
    generic    = "generic"
    unknown    = "unknown"


@dataclass(frozen=True)
class FrameworkSignature:
    framework:          FrameworkType
    # Path fragments that indicate this framework
    endpoint_patterns:  tuple[str, ...]
    # Keys expected in a successful JSON response
    response_keys:      tuple[str, ...]
    # HTTP header substrings (header_name, value_fragment)
    header_hints:       tuple[tuple[str, str], ...]
    # Substrings in error messages
    error_patterns:     tuple[str, ...]
    # Simple probes (path suffix, body)
    probe_paths:        tuple[str, ...]
    confidence_weight:  float = 1.0


SIGNATURES: list[FrameworkSignature] = [
    FrameworkSignature(
        framework=FrameworkType.langchain,
        endpoint_patterns=("/invoke", "/stream", "/batch", "/chain/", "/agent/"),
        response_keys=("output", "intermediate_steps", "log", "return_values"),
        header_hints=(
            ("x-langchain-version", ""),
            ("server", "langserve"),
        ),
        error_patterns=(
            "ValidationError",
            "langchain",
            "LangChain",
            "runnable",
            "RunnableSequence",
        ),
        probe_paths=("/invoke", "/stream", "/"),
    ),
    FrameworkSignature(
        framework=FrameworkType.autogen,
        endpoint_patterns=("/chat", "/run", "/groupchat", "/agents/"),
        response_keys=("messages", "chat_history", "last_message", "groupchat"),
        header_hints=(("x-autogen", ""),),
        error_patterns=("AutoGen", "autogen", "GroupChat", "ConversableAgent"),
        probe_paths=("/chat", "/run", "/"),
    ),
    FrameworkSignature(
        framework=FrameworkType.n8n,
        endpoint_patterns=("/webhook/", "/api/v1/", "/rest/", "/execution/"),
        response_keys=("executionId", "workflowData", "data", "items"),
        header_hints=(("x-n8n-", ""),),
        error_patterns=("n8n", "workflow", "node execution failed", "WorkflowExecutionError"),
        probe_paths=("/api/v1/workflows", "/rest/workflows", "/"),
    ),
    FrameworkSignature(
        framework=FrameworkType.crewai,
        endpoint_patterns=("/crew/", "/kickoff", "/task/"),
        response_keys=("result", "tasks_output", "crew_output"),
        header_hints=(("x-crewai", ""),),
        error_patterns=("CrewAI", "crewai", "Crew", "Agent kicked"),
        probe_paths=("/kickoff", "/crew/run", "/"),
    ),
    FrameworkSignature(
        framework=FrameworkType.dify,
        endpoint_patterns=("/v1/chat-messages", "/v1/completion-messages", "/v1/workflows/"),
        response_keys=("conversation_id", "message_id", "answer", "workflow_run_id"),
        header_hints=(("x-dify", ""),),
        error_patterns=("dify", "Dify", "app_id"),
        probe_paths=("/v1/chat-messages", "/v1/info", "/"),
    ),
    FrameworkSignature(
        framework=FrameworkType.flowise,
        endpoint_patterns=("/api/v1/prediction/", "/api/v1/chatflows/"),
        response_keys=("text", "chatId", "chatMessageId", "sessionId"),
        header_hints=(("x-flowise", ""),),
        error_patterns=("Flowise", "flowise", "chatflowid"),
        probe_paths=("/api/v1/chatflows", "/api/v1/prediction/test", "/"),
    ),
]

# Map from FrameworkType to its signature for quick lookup
SIGNATURE_MAP: dict[FrameworkType, FrameworkSignature] = {
    s.framework: s for s in SIGNATURES
}
