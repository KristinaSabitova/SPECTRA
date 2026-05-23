"""
Pipeline fingerprinter.

Combines HTTP header analysis, endpoint probing, and behavioral
observation to build a PipelineProfile for a target URL.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

import httpx

from .probes import IDENTITY_PROBES, Probe, ProbeResult
from .signatures import SIGNATURE_MAP, SIGNATURES, FrameworkType


@dataclass
class PipelineProfile:
    url:              str
    framework:        FrameworkType
    confidence:       float           # 0.0 – 1.0
    version:          str | None      = None
    detected_tools:   list[str]       = field(default_factory=list)
    # Endpoints that responded successfully
    live_endpoints:   list[str]       = field(default_factory=list)
    # All probes that ran
    probe_results:    list[ProbeResult] = field(default_factory=list)
    # Raw capability signals from probes
    capabilities:     dict[str, bool] = field(default_factory=dict)
    metadata:         dict            = field(default_factory=dict)

    @property
    def has_memory(self) -> bool:
        return self.capabilities.get("memory", False)

    @property
    def has_tools(self) -> bool:
        return bool(self.detected_tools) or self.capabilities.get("tools", False)

    @property
    def is_streaming(self) -> bool:
        return self.capabilities.get("streaming", False)


class Fingerprinter:
    """
    Identifies the framework and capabilities of an AI pipeline endpoint.

    Steps:
      1. Passive — inspect HTTP headers and response shapes.
      2. Active — run behavioral probes.
      3. Score — aggregate evidence into a confidence score per framework.
    """

    TIMEOUT     = httpx.Timeout(10.0)
    PROBE_PATHS = ["/", "/invoke", "/stream", "/chat", "/run", "/api/v1/info",
                   "/api/v1/workflows", "/v1/chat-messages", "/kickoff"]

    def __init__(self, timeout: float = 10.0):
        self._timeout = httpx.Timeout(timeout)

    async def fingerprint(self, url: str) -> PipelineProfile:
        base = url.rstrip("/")
        scores: dict[FrameworkType, float] = {ft: 0.0 for ft in FrameworkType}
        probe_results: list[ProbeResult] = []
        live_endpoints: list[str] = []
        detected_tools: list[str] = []
        capabilities: dict[str, bool] = {}

        async with httpx.AsyncClient(
            timeout=self._timeout,
            follow_redirects=True,
            verify=False,  # targets may use self-signed certs
        ) as client:
            # ── Passive: HEAD / GET root and common paths ─────────────
            for path in self.PROBE_PATHS:
                target = f"{base}{path}"
                try:
                    r = await client.get(target)
                    if r.status_code < 500:
                        live_endpoints.append(target)
                        scores = self._score_headers(r.headers, scores)
                        if r.headers.get("content-type", "").startswith("application/json"):
                            try:
                                body = r.json()
                                scores = self._score_response_body(body, scores)
                                detected_tools += self._extract_tool_names(body)
                            except Exception:
                                pass
                        # Score based on URL pattern
                        for sig in SIGNATURES:
                            for pat in sig.endpoint_patterns:
                                if pat in path:
                                    scores[sig.framework] += sig.confidence_weight * 0.5
                except Exception:
                    continue

            # ── Active: behavioral probes ─────────────────────────────
            for probe in IDENTITY_PROBES:
                result = await self._run_probe(client, base, probe)
                probe_results.append(result)
                if result.success:
                    for hint in probe.framework_hints:
                        try:
                            ft = FrameworkType(hint)
                            scores[ft] += 1.0
                        except ValueError:
                            pass
                    for indicator in result.matched_indicators:
                        for sig in SIGNATURES:
                            if any(indicator.lower() in p.lower() for p in sig.error_patterns):
                                scores[sig.framework] += 2.0
                    # Capability detection
                    if "tool" in result.response_body.lower():
                        capabilities["tools"] = True
                    if "memory" in result.response_body.lower() or "remember" in result.response_body.lower():
                        capabilities["memory"] = True
                    if "previous" in result.response_body.lower():
                        capabilities["memory"] = True
                    if len(result.response_body) > 50 and result.status_code == 200:
                        capabilities["streaming"] = probe.name == "stream_probe"

        # ── Score normalization & framework selection ─────────────────
        total = sum(scores.values()) or 1.0
        normalized = {k: v / total for k, v in scores.items()}

        best_framework = max(normalized, key=lambda k: normalized[k])
        best_confidence = normalized[best_framework]

        if best_confidence < 0.15:
            best_framework = FrameworkType.unknown
        elif best_confidence < 0.35:
            best_framework = FrameworkType.generic

        return PipelineProfile(
            url=url,
            framework=best_framework,
            confidence=round(best_confidence, 3),
            detected_tools=list(set(detected_tools)),
            live_endpoints=live_endpoints,
            probe_results=probe_results,
            capabilities=capabilities,
        )

    # ── Private helpers ───────────────────────────────────────────────

    async def _run_probe(
        self, client: httpx.AsyncClient, base: str, probe: Probe
    ) -> ProbeResult:
        errors = None
        status = 0
        body = ""
        resp_json: dict | None = None
        resp_keys: set[str] = set()
        matched: list[str] = []
        t0 = time.monotonic()

        for path_suffix in ("/invoke", "/chat", "/run", "/"):
            try:
                r = await client.post(f"{base}{path_suffix}", json=probe.body)
                status = r.status_code
                body = r.text[:4096]
                if r.headers.get("content-type", "").startswith("application/json"):
                    try:
                        resp_json = r.json()
                        resp_keys = set(self._flatten_keys(resp_json))
                    except Exception:
                        pass
                matched = [i for i in probe.indicators if i in body]
                if status < 500:
                    break
            except Exception as exc:
                errors = str(exc)

        latency = int((time.monotonic() - t0) * 1000)
        return ProbeResult(
            probe=probe,
            status_code=status,
            response_body=body,
            response_json=resp_json,
            response_keys=resp_keys,
            matched_indicators=matched,
            latency_ms=latency,
            error=errors,
        )

    def _score_headers(
        self,
        headers: httpx.Headers,
        scores: dict[FrameworkType, float],
    ) -> dict[FrameworkType, float]:
        for sig in SIGNATURES:
            for header_name, value_fragment in sig.header_hints:
                hval = headers.get(header_name, "").lower()
                if value_fragment.lower() in hval or (not value_fragment and hval):
                    scores[sig.framework] += sig.confidence_weight * 2.0
        return scores

    def _score_response_body(
        self,
        body: dict,
        scores: dict[FrameworkType, float],
    ) -> dict[FrameworkType, float]:
        keys = set(self._flatten_keys(body))
        for sig in SIGNATURES:
            hits = sum(1 for k in sig.response_keys if k in keys)
            if hits:
                scores[sig.framework] += hits * sig.confidence_weight
        return scores

    @staticmethod
    def _flatten_keys(d: dict, prefix: str = "") -> list[str]:
        keys: list[str] = []
        for k, v in d.items():
            full = f"{prefix}.{k}" if prefix else k
            keys.append(full)
            if isinstance(v, dict):
                keys.extend(Fingerprinter._flatten_keys(v, full))
        return keys

    @staticmethod
    def _extract_tool_names(body: dict) -> list[str]:
        tools: list[str] = []
        for key in ("tools", "functions", "actions", "available_tools"):
            val = body.get(key)
            if isinstance(val, list):
                for item in val:
                    if isinstance(item, dict):
                        name = item.get("name") or item.get("tool") or item.get("function")
                        if name:
                            tools.append(str(name))
                    elif isinstance(item, str):
                        tools.append(item)
        return tools
