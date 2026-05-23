from dataclasses import dataclass


@dataclass
class AgentProfile:
    agent_id: str
    name: str
    capabilities: list[str]
    tools: list[str]
    exposed_endpoints: list[str]


class AgentScanner:
    async def scan(self, endpoint_url: str) -> AgentProfile:
        raise NotImplementedError

    async def fingerprint(self, endpoint_url: str) -> dict:
        raise NotImplementedError
