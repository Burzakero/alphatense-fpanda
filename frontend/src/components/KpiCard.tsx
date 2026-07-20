import { formatCurrency, formatPct } from '../utils/format'
import { Card } from './ui/Card'

export function KpiCard({
  label,
  value,
  marginPct,
}: {
  label: string
  value: number
  marginPct?: number | null
}) {
  return (
    <Card className="p-4">
      <p className="text-sm text-slate-500 dark:text-slate-400">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-slate-900 dark:text-slate-50">
        {formatCurrency(value)}
      </p>
      {marginPct !== undefined && (
        <p className="mt-1 text-xs text-slate-400">margin {formatPct(marginPct)}</p>
      )}
    </Card>
  )
}
