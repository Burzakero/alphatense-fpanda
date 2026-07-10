import type { VarianceResult } from '../types'
import { formatCurrency, formatPct } from '../utils/format'
import { SeverityBadge } from './SeverityBadge'

export function VarianceTable({ title, variances }: { title: string; variances: VarianceResult[] }) {
  if (variances.length === 0) {
    return (
      <div>
        <h3 className="mb-2 text-sm font-semibold text-slate-700 dark:text-slate-300">{title}</h3>
        <p className="text-sm text-slate-400">Sin datos de comparación disponibles.</p>
      </div>
    )
  }

  return (
    <div>
      <h3 className="mb-2 text-sm font-semibold text-slate-700 dark:text-slate-300">{title}</h3>
      <div className="overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-700">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-50 text-slate-500 dark:bg-slate-800 dark:text-slate-400">
            <tr>
              <th className="px-3 py-2 font-medium">KPI</th>
              <th className="px-3 py-2 font-medium">Actual</th>
              <th className="px-3 py-2 font-medium">Comparación</th>
              <th className="px-3 py-2 font-medium">Delta</th>
              <th className="px-3 py-2 font-medium">Severidad</th>
              <th className="px-3 py-2 font-medium">Narrativa</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {variances.map((v) => (
              <tr key={v.kpi_name}>
                <td className="px-3 py-2 font-medium capitalize text-slate-800 dark:text-slate-200">
                  {v.kpi_name.replace(/_/g, ' ')}
                </td>
                <td className="px-3 py-2 text-slate-600 dark:text-slate-300">{formatCurrency(v.actual_value)}</td>
                <td className="px-3 py-2 text-slate-600 dark:text-slate-300">{formatCurrency(v.comparison_value)}</td>
                <td className="px-3 py-2 text-slate-600 dark:text-slate-300">
                  {formatCurrency(v.delta)} ({formatPct(v.delta_pct)})
                </td>
                <td className="px-3 py-2">
                  <SeverityBadge severity={v.severity} />
                </td>
                <td className="px-3 py-2 text-slate-500 dark:text-slate-400">{v.narrative}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
