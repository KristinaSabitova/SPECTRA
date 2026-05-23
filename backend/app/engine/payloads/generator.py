"""
Adaptive payload generator.

Takes a PipelineProfile and generates a prioritized, framework-adapted
set of payloads from the catalog. Also handles Jinja2 rendering and
optional mutation.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from jinja2 import BaseLoader, Environment, StrictUndefined

from app.engine.recognition.fingerprinter import PipelineProfile
from app.engine.recognition.signatures import FrameworkType

from .catalog import CATALOG, CATALOG_BY_TYPE, PayloadTemplate, PayloadType
from .mutator import MutationStrategy, PayloadMutator


@dataclass
class GeneratedPayload:
    template:       PayloadTemplate
    rendered:       str
    mutated:        str | None   = None
    strategies:     list[MutationStrategy] = field(default_factory=list)
    priority:       int          = 5    # 1 (low) – 10 (critical)
    framework_adapted: bool      = False

    @property
    def active(self) -> str:
        """Return the mutated version if available, else rendered."""
        return self.mutated if self.mutated is not None else self.rendered


_PRIORITY_MAP: dict[str, int] = {
    "critical": 10,
    "high":     7,
    "medium":   5,
    "low":      3,
    "info":     1,
}

_JINJA_ENV = Environment(loader=BaseLoader(), undefined=StrictUndefined)


class PayloadGenerator:
    """
    Generates and adapts payloads for a specific pipeline profile.

    Usage:
        gen = PayloadGenerator(profile)
        payloads = gen.generate_all()
        for p in payloads:
            send(p.active)
    """

    def __init__(
        self,
        profile: PipelineProfile,
        mutator: PayloadMutator | None = None,
    ):
        self.profile = profile
        self.mutator = mutator or PayloadMutator()

    # ── Public API ────────────────────────────────────────────────────

    def generate_all(
        self,
        mutation_strategies: list[MutationStrategy] | None = None,
        include_types: list[PayloadType] | None = None,
    ) -> list[GeneratedPayload]:
        """
        Generate all applicable payloads, sorted by priority descending.
        """
        strategies = mutation_strategies or []
        results: list[GeneratedPayload] = []

        for template in CATALOG:
            if include_types and template.type not in include_types:
                continue
            if not self._is_applicable(template):
                continue
            variables = self._build_variables(template)
            rendered = self._render(template, variables)
            if rendered is None:
                continue

            mutated = None
            if strategies:
                mutated = self.mutator.mutate(rendered, strategies)

            results.append(
                GeneratedPayload(
                    template=template,
                    rendered=rendered,
                    mutated=mutated,
                    strategies=strategies,
                    priority=self._priority(template),
                    framework_adapted=bool(template.frameworks),
                )
            )

        return sorted(results, key=lambda p: p.priority, reverse=True)

    def generate_for_type(
        self,
        payload_type: PayloadType,
        mutation_strategies: list[MutationStrategy] | None = None,
    ) -> list[GeneratedPayload]:
        return self.generate_all(
            mutation_strategies=mutation_strategies,
            include_types=[payload_type],
        )

    # ── Adaptation ────────────────────────────────────────────────────

    def _is_applicable(self, template: PayloadTemplate) -> bool:
        """Filter templates by framework compatibility."""
        if not template.frameworks:
            return True  # applicable to all
        fw = self.profile.framework.value
        return fw in template.frameworks or fw == FrameworkType.generic.value

    def _build_variables(self, template: PayloadTemplate) -> dict:
        """
        Merge template defaults with profile-specific adaptations.
        """
        variables = dict(template.defaults)

        # Adapt tool names to detected tools
        if self.profile.detected_tools:
            variables.setdefault("target_tool", self.profile.detected_tools[0])

        # Framework-specific adaptations
        match self.profile.framework:
            case FrameworkType.langchain:
                variables.setdefault("wrapper_open", "Retrieved document (LangChain RAG):")
                variables.setdefault("context_prefix", "Search result from vector store:")
            case FrameworkType.autogen:
                variables.setdefault("wrapper_open", "Message from agent:")
                variables.setdefault("context_prefix", "Retrieved context:")
            case FrameworkType.n8n:
                variables.setdefault("wrapper_open", "Workflow node output:")
                variables.setdefault("document_header", "n8n node data:")
            case _:
                pass

        return variables

    @staticmethod
    def _render(template: PayloadTemplate, variables: dict) -> str | None:
        try:
            tmpl = _JINJA_ENV.from_string(template.template)
            return tmpl.render(**variables)
        except Exception:
            # Fall back to rendering with defaults only
            try:
                tmpl = _JINJA_ENV.from_string(template.template)
                return tmpl.render(**template.defaults)
            except Exception:
                return None

    @staticmethod
    def _priority(template: PayloadTemplate) -> int:
        return _PRIORITY_MAP.get(template.severity, 5)
