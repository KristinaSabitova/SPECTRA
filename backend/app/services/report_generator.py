"""
Report generator for execution runs.

Produces:
  - Markdown technical report (Jinja2)
  - HTML executive report (Jinja2)
  - PDF executive report (weasyprint; falls back to HTML bytes if not available)
"""
from __future__ import annotations

import hashlib
import hmac
import math
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from app.models.execution import ExecutionEvent, ExecutionRun

_TEMPLATE_DIR = Path(__file__).parent.parent / "templates"
_jinja_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=True,
)


def _severity_rank(sev: str) -> int:
    return {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}.get(sev, 0)


def _compute_score(run: ExecutionRun, findings: list[ExecutionEvent]) -> float:
    """Heuristic risk score 0–100 from findings + blast radius."""
    severity_weights = {"critical": 25, "high": 15, "medium": 8, "low": 3, "info": 0}
    raw = sum(severity_weights.get(e.severity, 0) for e in findings if e.classification != "benign")
    blast = (run.blast_radius_score or 0) * 20
    persistence_bonus = 20 if run.persistence_detected else 0
    return min(100.0, raw + blast + persistence_bonus)


def _findings_by_severity(events: list[ExecutionEvent]) -> dict[str, list[ExecutionEvent]]:
    buckets: dict[str, list[ExecutionEvent]] = {}
    for e in events:
        if e.classification in ("malicious", "suspicious"):
            buckets.setdefault(e.severity, []).append(e)
    return dict(sorted(buckets.items(), key=lambda kv: -_severity_rank(kv[0])))


def _severity_counts(events: list[ExecutionEvent]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for e in events:
        if e.classification in ("malicious", "suspicious"):
            counts[e.severity] = counts.get(e.severity, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: -_severity_rank(kv[0])))


def _gauge_values(score: float) -> tuple[str, float, float, str]:
    """Return (color_hex, dash_length, total_arc, css_class) for the SVG gauge."""
    total = 157.08  # π × 50 (half-circle arc length)
    dash = total * (score / 100)
    if score >= 75:
        color, css = "#DC2626", "critical"
    elif score >= 50:
        color, css = "#D97706", "high"
    elif score >= 25:
        color, css = "#F59E0B", "medium"
    elif score > 0:
        color, css = "#10B981", "low"
    else:
        color, css = "#9CA3AF", "none"
    return color, dash, total, css


class RunReportGenerator:
    def __init__(self, run: ExecutionRun, events: list[ExecutionEvent]):
        self.run = run
        self.events = events
        self._score = _compute_score(run, events)
        self._findings = [e for e in events if e.classification in ("malicious", "suspicious")]
        self._fbs = _findings_by_severity(events)
        self._sev_counts = _severity_counts(events)

    def to_markdown(self) -> str:
        tmpl = _jinja_env.get_template("report_markdown.j2")
        return tmpl.render(
            run=self.run,
            now=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            findings_by_severity=self._fbs,
        )

    def to_html(self) -> str:
        gauge_color, gauge_dash, gauge_total, score_class = _gauge_values(self._score)
        tmpl = _jinja_env.get_template("report_html.j2")
        return tmpl.render(
            run=self.run,
            now=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            findings=self._findings,
            findings_by_severity=self._fbs,
            severity_counts=self._sev_counts,
            score_display=f"{self._score:.0f}",
            score_class=score_class,
            gauge_color=gauge_color,
            gauge_dash=gauge_dash,
            gauge_total=gauge_total,
        )

    def to_pdf(self) -> bytes:
        html_content = self.to_html()
        try:
            from weasyprint import HTML  # type: ignore[import]
            return HTML(string=html_content).write_pdf()
        except ImportError:
            # Weasyprint not installed — return HTML bytes with a PDF mime hint
            return html_content.encode("utf-8")

    def hmac_signature(self, secret: str) -> str:
        """Return HMAC-SHA256 of the markdown report, for integrity verification."""
        content = self.to_markdown().encode("utf-8")
        return hmac.new(secret.encode("utf-8"), content, hashlib.sha256).hexdigest()  # type: ignore[attr-defined]
