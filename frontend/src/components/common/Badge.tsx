type BadgeVariant =
  | 'critical' | 'high' | 'medium' | 'low' | 'info'
  | 'pending' | 'queued' | 'running' | 'completed' | 'failed' | 'cancelled'
  | 'malicious' | 'suspicious' | 'benign' | 'unknown'
  | 'admin' | 'senior' | 'junior'

interface BadgeProps {
  variant: BadgeVariant
  label: string
}

export default function Badge({ variant, label }: BadgeProps) {
  return (
    <span className={`badge badge-${variant}`}>{label}</span>
  )
}
