interface SpinnerProps {
  size?: 'sm' | 'md' | 'lg'
  page?: boolean
}

export default function Spinner({ size = 'md', page = false }: SpinnerProps) {
  const el = <span className={`spinner spinner-${size}`} />
  if (page) return <div className="spinner-page">{el}</div>
  return el
}
