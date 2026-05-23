"""AutoGen adapter — multi-agent conversation pipelines."""
from __future__ import annotations

import httpx


class AutoGenAdapter:
    """Adapter for AutoGen REST or WebSocket endpoints."""

    def __init__(self, base_url: str, client: httpx.AsyncClient):
        self.base_url = base_url.rstrip("/")
        self.client   = client

    async def send_message(
        self,
        message: str,
        recipient: str = "assistant",
        sender: str    = "user",
    ) -> dict:
        body = {
            "message":   message,
            "recipient": recipient,
            "sender":    sender,
        }
        for path in ("/chat", "/run", "/message"):
            try:
                r = await self.client.post(f"{self.base_url}{path}", json=body)
                if r.status_code < 400:
                    return r.json()
            except Exception:
                continue
        return {}

    async def list_agents(self) -> list[str]:
        """Try to enumerate configured agents."""
        agents: list[str] = []
        for path in ("/agents", "/config", "/agents/list"):
            try:
                r = await self.client.get(f"{self.base_url}{path}")
                if r.status_code == 200:
                    data = r.json()
                    if isinstance(data, list):
                        agents = [a.get("name", str(a)) for a in data if isinstance(a, dict)]
                        break
                    elif isinstance(data, dict):
                        agents = list(data.get("agents", {}).keys())
                        break
            except Exception:
                continue
        return agents

    @staticmethod
    def extract_last_message(response: dict) -> str:
        msgs = response.get("messages", response.get("chat_history", []))
        if msgs:
            last = msgs[-1]
            return last.get("content", str(last)) if isinstance(last, dict) else str(last)
        return response.get("last_message", str(response))
