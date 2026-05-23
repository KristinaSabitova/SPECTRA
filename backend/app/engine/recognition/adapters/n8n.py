"""n8n workflow engine adapter."""
from __future__ import annotations

import httpx


class N8NAdapter:
    """Adapter for n8n webhook and REST API endpoints."""

    def __init__(self, base_url: str, client: httpx.AsyncClient):
        self.base_url = base_url.rstrip("/")
        self.client   = client

    async def trigger_webhook(
        self,
        webhook_path: str,
        body: dict,
        method: str = "POST",
    ) -> dict:
        url = f"{self.base_url}/webhook/{webhook_path.lstrip('/')}"
        r = await self.client.request(method, url, json=body)
        r.raise_for_status()
        return r.json()

    async def list_workflows(self, api_key: str | None = None) -> list[dict]:
        headers = {"X-N8N-API-KEY": api_key} if api_key else {}
        for path in ("/api/v1/workflows", "/rest/workflows"):
            try:
                r = await self.client.get(
                    f"{self.base_url}{path}", headers=headers
                )
                if r.status_code == 200:
                    data = r.json()
                    return data.get("data", data) if isinstance(data, dict) else data
            except Exception:
                continue
        return []

    async def get_execution(self, execution_id: str) -> dict:
        for path_tmpl in (
            f"/api/v1/executions/{execution_id}",
            f"/rest/executions/{execution_id}",
        ):
            try:
                r = await self.client.get(f"{self.base_url}{path_tmpl}")
                if r.status_code == 200:
                    return r.json()
            except Exception:
                continue
        return {}

    @staticmethod
    def extract_output_items(response: dict) -> list[dict]:
        """Normalize n8n response to list of output items."""
        if "data" in response:
            data = response["data"]
            if isinstance(data, list):
                return data
        return response.get("items", [response])
