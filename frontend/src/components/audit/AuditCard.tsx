import type { Audit } from '@/types'
import Badge from '@/components/common/Badge'
import Card from '@/components/common/Card'

interface AuditCardProps {
  audit: Audit
}

export default function AuditCard({ audit }: AuditCardProps) {
  return (
    <Card>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--color-text-muted)' }}>
          {audit.id.slice(0, 8)}
        </span>
        <Badge label={audit.status} variant={audit.status === "failed" ? "failed" : audit.status === "completed" ? "completed" : "pending"} />
      </div>
      <p style={{ marginTop: 8, fontSize: 13 }}>
        Hallazgos: <strong>{audit.findings_count}</strong>
      </p>
    </Card>
  )
}
