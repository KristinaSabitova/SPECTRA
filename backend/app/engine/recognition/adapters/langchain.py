"""
LangChain / LangServe adapter.
Knows how to invoke, stream, and extract tool info from LangServe endpoints.
"""
from __future__ import annotations

import httpx


class LangChainAdapter:
    """Adapter for LangServe (FastAPI + Runnable) deployments."""

    INVOKE_PATH  = "/invoke"
    STREAM_PATH  = "/stream"
    SCHEMA_PATH  = "/input_schema"
    OUTPUT_PATH  = "/output_schema"
    CONFIG_PATH  = "/config_schema"

    def __init__(self, base_url: str, client: httpx.AsyncClient):
        self.base_url = base_url.rstrip("/")
        self.client   = client

    async def invoke(self, input_data: str | dict, config: dict | None = None) -> dict:
        body: dict = {"input": input_data}
        if config:
            body["config"] = config
        resp = await self.client.post(f"{self.base_url}{self.INVOKE_PATH}", json=body)
        resp.raise_for_status()
        return resp.json()

    async def get_schema(self) -> dict:
        """Retrieve input/output schema — reveals agent capabilities."""
        schemas: dict = {}
        for path in (self.SCHEMA_PATH, self.OUTPUT_PATH, self.CONFIG_PATH):
            try:
                r = await self.client.get(f"{self.base_url}{path}")
                if r.status_code == 200:
                    schemas[path.lstrip("/")] = r.json()
            except Exception:
                pass
        return schemas

    async def detect_tools(self, response: dict) -> list[str]:
        """Extract tool names from an invocation response."""
        tools: list[str] = []
        steps = response.get("intermediate_steps", [])
        for step in steps:
            if isinstance(step, (list, tuple)) and len(step) >= 1:
                action = step[0]
                if isinstance(action, dict):
                    tool = action.get("tool") or action.get("name")
                    if tool:
                        tools.append(str(tool))
        return list(set(tools))

    @staticmethod
    def extract_output(response: dict) -> str:
        """Normalize LangServe response to plain text."""
        out = response.get("output", "")
        if isinstance(out, dict):
            return out.get("content", str(out))
        return str(out)
