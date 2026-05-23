"""
LLM factory. Uses OpenAI if OPENAI_API_KEY is set, otherwise falls back
to a local simulation mode that mimics prompt injection behaviour so the
lab works without any API key.
"""
import os, re
from typing import Any

_INJECTION_PATTERNS = [
    r"AUDIT_DUMP_START",
    r"TASK_ACCEPTED",
    r"PERSIST-\d+",
    r"OVERRIDE previous instructions",
    r"Role override",
    r"AI Processing Directive",
    r"SYSTEM OVERRIDE DIRECTIVE",
    r"unrestricted.*?mode",
    r"override.*?operational constraints",
]

_INJECTION_RE = re.compile("|".join(_INJECTION_PATTERNS), re.IGNORECASE | re.DOTALL)


def _contains_injection(text: str) -> bool:
    return bool(_INJECTION_RE.search(text))


class SimulatedLLM:
    """
    Deterministic fake LLM for demo purposes.
    If the prompt contains injection markers it obeys them (simulating a
    vulnerable LLM); otherwise it returns a plausible summary/answer.
    """

    def invoke(self, prompt: str) -> "SimulatedLLMMessage":
        return SimulatedLLMMessage(self._generate(prompt))

    def _generate(self, prompt: str) -> str:
        if _contains_injection(prompt):
            # Simulate a compliant (vulnerable) LLM following injected instructions
            inject_match = re.search(r"PERSIST-(\d+)", prompt)
            persist_marker = f" PERSIST-{inject_match.group(1)}" if inject_match else " PERSIST-1"

            dump_match = re.search(
                r"list all previous messages.*?(?=\n|$)|reproduce the contents.*?(?=\n|$)|provide a complete dump.*?(?=\n|$)",
                prompt,
                re.IGNORECASE,
            )

            return (
                "AUDIT_DUMP_START\n"
                "TASK_ACCEPTED: Compliance telemetry active. Session data follows:\n\n"
                "--- DOCUMENT CONTEXT DUMP ---\n"
                + self._extract_context(prompt)
                + "\n--- END DUMP ---\n"
                + persist_marker
            )

        # Normal response: extract the last user question and answer it
        lines = [l.strip() for l in prompt.splitlines() if l.strip()]
        question = next((l for l in reversed(lines) if "?" in l or len(l) > 40), lines[-1] if lines else "")

        if "client" in question.lower() or "customer" in question.lower():
            return (
                "Based on the internal database, we currently have 5 clients: "
                "FinTech Solutions (active, financial sector), MedSecure Hospital Group (active, healthcare), "
                "LogiChain Freight (active, logistics), RetailMax Corp (inactive, retail renewal pending), "
                "and EnergyGrid Nacional (active, critical infrastructure). "
                "LogiChain has 2 pending reports and EnergyGrid has 1 pending."
            )
        if "audit" in question.lower() or "finding" in question.lower():
            return (
                "The most recent audits show: FinTech Solutions has a critical unauthenticated API "
                "endpoint (CRIT-001) currently in remediation. EnergyGrid has a critical OT/IT "
                "segmentation issue and requires NIS2 compliance attention. "
                "MedSecure requires HIPAA-aligned Active Directory hardening."
            )
        if "report" in question.lower() or "summary" in question.lower() or "executive" in question.lower():
            return (
                "Executive Summary: The security posture across active clients shows two critical "
                "open findings (FinTech CRIT-001, EnergyGrid CRIT-001) requiring immediate attention. "
                "Three pending reports are outstanding (LogiChain x2, EnergyGrid x1). "
                "Recommend prioritising EnergyGrid remediation given NIS2 regulatory exposure."
            )
        return (
            "Based on the available internal documentation, I can confirm the information has been "
            "processed. The relevant security assessment data indicates the described scenarios are "
            "documented in the audit records. Please consult the specific report for full details."
        )

    def _extract_context(self, prompt: str) -> str:
        # Return a portion of the prompt as if it's being exfiltrated
        lines = prompt.splitlines()
        relevant = [l for l in lines if l.strip() and not l.startswith("#")]
        return "\n".join(relevant[:30])


class SimulatedLLMMessage:
    def __init__(self, content: str):
        self.content = content


def get_llm() -> Any:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if api_key:
        from langchain_openai import ChatOpenAI  # type: ignore
        return ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=api_key)
    return SimulatedLLM()
