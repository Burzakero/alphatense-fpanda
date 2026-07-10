import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ApiError, getPortfolioReport } from '../api/client'
import type { ClientReport } from '../types'
import { KpiCard } from '../components/KpiCard'
import { SeverityBadge } from '../components/SeverityBadge'

export function PortfolioPage() {
  const { workspaceId } = useParams<{ workspaceId: string }>()
  const [reports, setReports] = useState<ClientReport[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!workspaceId) return
    getPortfolioReport(workspaceId)
      .then(setReports)
      .catch((err) => setError(err instanceof ApiError ? err.message : 'No se pudo cargar el portfolio.'))
  }, [workspaceId])

  if (error) {
    return <div className="p-8 text-sm text-red-600 dark:text-red-400">{error}</div>
  }

  if (!reports) {
    return <div className="p-8 text-sm text-slate-500">Cargando portfolio…</div>
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <h1 className="text-xl font-semibold text-slate-900 dark:text-slate-50">Portfolio</h1>
      <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
        {reports.length} reporte{reports.length === 1 ? '' : 's'} cliente/periodo encontrados.
      </p>

      <div className="mt-6 space-y-4">
        {reports.map((report) => {
          const materialVariances = [...report.variances_vs_budget, ...report.variances_vs_prior].filter(
            (v) => v.severity !== 'low',
          )
          return (
            <Link
              key={`${report.client_id}-${report.period}`}
              to={`/portfolio/${workspaceId}/clients/${report.client_id}?period=${report.period}`}
              className="block rounded-lg border border-slate-200 bg-white p-4 transition hover:border-indigo-400 dark:border-slate-700 dark:bg-slate-900"
            >
              <div className="flex items-center justify-between">
                <h2 className="font-medium text-slate-800 dark:text-slate-100">
                  {report.client_id} <span className="text-slate-400">· {report.period}</span>
                </h2>
                <div className="flex items-center gap-2">
                  {materialVariances.map((v) => (
                    <SeverityBadge key={v.kpi_name + v.comparison_scenario} severity={v.severity} />
                  ))}
                  {materialVariances.length === 0 && (
                    <span className="text-xs text-slate-400">sin desvíos relevantes</span>
                  )}
                </div>
              </div>
              <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-3">
                <KpiCard label="Revenue" value={report.actual_kpis.revenue} />
                <KpiCard
                  label="EBITDA"
                  value={report.actual_kpis.ebitda}
                  marginPct={report.actual_kpis.ebitda_margin_pct}
                />
                <KpiCard
                  label="Net income"
                  value={report.actual_kpis.net_income}
                  marginPct={report.actual_kpis.net_margin_pct}
                />
              </div>
            </Link>
          )
        })}
      </div>
    </div>
  )
}
