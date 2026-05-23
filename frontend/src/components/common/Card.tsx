import type { ReactNode } from 'react'

interface CardProps {
  title?: string
  action?: ReactNode
  children: ReactNode
  className?: string
}

export default function Card({ title, action, children, className = '' }: CardProps) {
  return (
    <div className={`card ${className}`}>
      {(title || action) && (
        <div className="card-header">
          {title && <span className="card-title">{title}</span>}
          {action}
        </div>
      )}
      {children}
    </div>
  )
}
