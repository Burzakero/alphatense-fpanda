import type { VarianceResult } from '../types'
import { formatCurrency, formatPct } from '../utils/format'
import { SeverityBadge } from './SeverityBadge'
import { tableShell, tableHead, tableHeadCell, tableBody, tableCell, tableCellStrong } from './ui/table'

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
      <div className={tableShell}>
        <table className="w-full text-left text-sm">
          <thead className={tableHead}>
            <tr>
              <th className={tableHeadCell}>KPI</th>
              <th className={tableHeadCell}>Actual</th>
              <th className={tableHeadCell}>Comparación</th>
              <th className={tableHeadCell}>Delta</th>
              <th className={tableHeadCell}>Severidad</th>
              <th className={tableHeadCell}>Narrativa</th>
            </tr>
          </thead>
          <tbody className={tableBody}>
            {variances.map((v) => (
              <tr key={v.kpi_name}>
                <td className={`${tableCellStrong} capitalize`}>{v.kpi_name.replace(/_/g, ' ')}</td>
                <td className={tableCell}>{formatCurrency(v.actual_value)}</td>
                <td className={tableCell}>{formatCurrency(v.comparison_value)}</td>
                <td className={tableCell}>
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
