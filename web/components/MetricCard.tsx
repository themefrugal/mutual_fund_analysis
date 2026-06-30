import { cn } from '@/lib/utils'

interface MetricCardProps {
  label: string
  value: string
  sub?: string
  highlight?: 'gain' | 'loss' | 'accent' | 'neutral'
  className?: string
}

export default function MetricCard({
  label,
  value,
  sub,
  highlight = 'neutral',
  className,
}: MetricCardProps) {
  const valueClass = {
    gain: 'text-gain',
    loss: 'text-loss',
    accent: 'text-accent',
    neutral: 'text-text',
  }[highlight]

  return (
    <div className={cn('rounded-xl border border-border bg-card p-4 flex flex-col gap-1', className)}>
      <p className="text-xs font-medium uppercase tracking-wider text-muted">{label}</p>
      <p className={cn('text-2xl font-bold', valueClass)}>{value}</p>
      {sub && <p className="text-xs text-muted">{sub}</p>}
    </div>
  )
}
