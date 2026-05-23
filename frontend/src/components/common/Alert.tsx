import { AlertCircle, CheckCircle, Info, AlertTriangle } from 'lucide-react'

type AlertType = 'error' | 'success' | 'warning' | 'info'

const icons = {
  error:   AlertCircle,
  success: CheckCircle,
  warning: AlertTriangle,
  info:    Info,
}

interface AlertProps {
  type: AlertType
  message: string
}

export default function Alert({ type, message }: AlertProps) {
  const Icon = icons[type]
  return (
    <div className={`alert alert-${type}`} role="alert">
      <Icon />
      <span>{message}</span>
    </div>
  )
}
