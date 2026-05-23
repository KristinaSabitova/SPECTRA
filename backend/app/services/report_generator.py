from app.services.pipeline_auditor import Finding


class ReportGenerator:
    def __init__(self, audit_id: str, findings: list[Finding]):
        self.audit_id = audit_id
        self.findings = findings

    def generate(self) -> dict:
        severity_counts = self._count_by_severity()
        return {
            "audit_id": self.audit_id,
            "total_findings": len(self.findings),
            "severity_summary": severity_counts,
            "findings": [self._serialize_finding(f) for f in self.findings],
        }

    def _count_by_severity(self) -> dict:
        counts: dict[str, int] = {}
        for f in self.findings:
            counts[f.severity] = counts.get(f.severity, 0) + 1
        return counts

    def _serialize_finding(self, finding: Finding) -> dict:
        return {
            "type": finding.type,
            "severity": finding.severity,
            "description": finding.description,
            "agent_id": finding.agent_id,
            "evidence": finding.evidence,
        }
