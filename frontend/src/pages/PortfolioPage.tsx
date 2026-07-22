import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { FileSpreadsheet, MessageCircle } from 'lucide-react'
import { API_BASE_URL, ApiError, getPortfolioReport, getToken } from '../api/client'
import type { ClientReport } from '../types'
import { KpiCard } from '../components/KpiCard'
import { SeverityBadge } from '../components/SeverityBadge'
import { InvoiceUpload } from '../components/InvoiceUpload'
import { PageHeading } from '../components/ui/PageHeading'

interface ClientGroup {
  clientId: string
  periods: ClientReport[]
  latest: ClientReport
}

function groupByClient(reports: ClientReport[]): ClientGroup[] {
  const byClient = new Map<string, ClientReport[]>()
  for (const report of reports) {
    const existing = byClient.get(report.client_id) ?? []
    existing.push(report)
    byClient.set(report.client_id, existing)
  }
  return Array.from(byClient.entries())
    .map(([clientId, periods]) => {
      const sorted = [...periods].sort((a, b) => b.period.localeCompare(a.period))
      return { clientId, periods: sorted, latest: sorted[0] }
    })
    .sort((a, b) => a.clientId.localeCompare(b.clientId))
}

export function PortfolioPage() {
  const { workspaceId } = useParams<{ workspaceId: string }>()
  const [reports, setReports] = useState<ClientReport[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!workspaceId) return
    getPortfolioReport(workspaceId)
      .then(setReports)
      .catch((err) => setError(err instanceof ApiError ? err.message : 'Could not load the portfolio.'))
  }, [workspaceId])

  if (error) {
    return <div className="p-8 text-sm text-red-600 dark:text-red-400">{error}</div>
  }

  if (!reports) {
    return <div className="p-8 text-sm text-slate-500">Loading portfolio…</div>
  }

  const groups = groupByClient(reports)
  const exportParams = new URLSearchParams(getToken() ? { token: getToken()! } : {})

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <PageHeading
        title="Portfolio"
        subtitle={`${groups.length} client${groups.length === 1 ? '' : 's'} · ${reports.length} report${
          reports.length === 1 ? '' : 's'
        } on file.`}
        action={
          <div className="flex items-center gap-4">
            <a
              href={`${API_BASE_URL}/workspaces/${workspaceId}/export/excel?${exportParams}`}
              className="inline-flex items-center gap-1.5 text-sm text-brand-600 hover:underline dark:text-brand-400"
            >
              <FileSpreadsheet className="h-4 w-4" />
              Export for Power BI
            </a>
            <Link
              to={`/portfolio/${workspaceId}/chat`}
              className="inline-flex items-center gap-1.5 text-sm text-brand-600 hover:underline dark:text-brand-400"
            >
              <MessageCircle className="h-4 w-4" />
              Ask the AI analyst
            </Link>
          </div>
        }
      />

      <div className="mt-4">{workspaceId && <InvoiceUpload workspaceId={workspaceId} />}</div>

      <div className="mt-6 space-y-4">
        {groups.map((group) => {
          const materialVariances = group.periods
            .flatMap((report) => [...report.variances_vs_budget, ...report.variances_vs_prior])
            .filter((v) => v.severity !== 'low')
          return (
            <Link
              key={group.clientId}
              to={`/portfolio/${workspaceId}/clients/${group.clientId}`}
              className="block rounded-lg border border-slate-200 bg-white p-4 shadow-sm transition hover:border-brand-400 hover:shadow-md dark:border-slate-700 dark:bg-slate-900"
            >
              <div className="flex items-center justify-between">
                <h2 className="font-medium text-slate-800 dark:text-slate-100">
                  {group.clientId} <span className="text-slate-400">· latest: {group.latest.period}</span>
                </h2>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-slate-400">
                    {group.periods.length} period{group.periods.length === 1 ? '' : 's'} on file
                  </span>
                  {materialVariances.length > 0 ? (
                    <SeverityBadge
                      severity={materialVariances.some((v) => v.severity === 'high') ? 'high' : 'medium'}
                    />
                  ) : (
                    <span className="text-xs text-slate-400">no material variances</span>
                  )}
                </div>
              </div>
              <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-3">
                <KpiCard label="Revenue" value={group.latest.actual_kpis.revenue} />
                <KpiCard
                  label="EBITDA"
                  value={group.latest.actual_kpis.ebitda}
                  marginPct={group.latest.actual_kpis.ebitda_margin_pct}
                />
                <KpiCard
                  label="Net income"
                  value={group.latest.actual_kpis.net_income}
                  marginPct={group.latest.actual_kpis.net_margin_pct}
                />
              </div>
            </Link>
          )
        })}
      </div>
    </div>
  )
}
