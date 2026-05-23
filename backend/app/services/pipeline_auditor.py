from dataclasses import dataclass, field
from enum import Enum


class FindingType(str, Enum):
    prompt_injection = "prompt_injection"
    privilege_escalation = "privilege_escalation"
    context_leak = "context_leak"
    unauthorized_tool_call = "unauthorized_tool_call"
    insecure_output = "insecure_output"


@dataclass
class Finding:
    type: FindingType
    severity: str
    description: str
    agent_id: str | None = None
    evidence: dict = field(default_factory=dict)


class PipelineAuditor:
    def __init__(self, pipeline_id: str):
        self.pipeline_id = pipeline_id
        self.findings: list[Finding] = []

    async def run(self) -> list[Finding]:
        await self._check_prompt_injection()
        await self._check_tool_permissions()
        await self._check_context_boundaries()
        return self.findings

    async def _check_prompt_injection(self):
        pass

    async def _check_tool_permissions(self):
        pass

    async def _check_context_boundaries(self):
        pass
