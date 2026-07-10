import { formatCurrency, formatPct } from '../utils/format'

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
    <div className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900">
      <p className="text-sm text-slate-500 dark:text-slate-400">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-slate-900 dark:text-slate-50">
        {formatCurrency(value)}
      </p>
      {marginPct !== undefined && (
        <p className="mt-1 text-xs text-slate-400">margen {formatPct(marginPct)}</p>
      )}
    </div>
  )
}
