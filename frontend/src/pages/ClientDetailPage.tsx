import { useEffect, useState } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import {
  API_BASE_URL,
  ApiError,
  getClientForecast,
  getClientReport,
  getPortfolioReport,
  getToken,
} from '../api/client'
import type { ClientReport, ForecastResult, VarianceResult } from '../types'
import { KpiCard } from '../components/KpiCard'
import { VarianceTable } from '../components/VarianceTable'
import { ForecastChart } from '../components/ForecastChart'
import { AgingSection } from '../components/AgingSection'
import { CashFlowChart } from '../components/CashFlowChart'
import { SeverityBadge } from '../components/SeverityBadge'
import { BackLink } from '../components/ui/BackLink'
import { ButtonLink } from '../components/ui/Button'
import { Tabs } from '../components/ui/Tabs'
import type { TabItem } from '../components/ui/Tabs'

const TABS = [
  { key: 'overview', label: 'Overview' },
  { key: 'variance', label: 'Variance' },
  { key: 'forecast', label: 'Forecast' },
  { key: 'aging-cash-flow', label: 'Aging & Cash Flow' },
]

function topMaterialVariances(report: ClientReport, limit = 3): VarianceResult[] {
  return [...report.variances_vs_budget, ...report.variances_vs_prior]
    .filter((v) => v.severity !== 'low')
    .sort((a, b) => Math.abs(b.delta_pct ?? 0) - Math.abs(a.delta_pct ?? 0))
    .slice(0, limit)
}

export function ClientDetailPage() {
  const { workspaceId, clientId, tab } = useParams<{
    workspaceId: string
    clientId: string
    tab?: string
  }>()
  const activeTab = tab ?? 'overview'
  const [searchParams, setSearchParams] = useSearchParams()
  const periodParam = searchParams.get('period')

  const [periods, setPeriods] = useState<string[] | null>(null)
  const [periodsError, setPeriodsError] = useState<string | null>(null)

  const [report, setReport] = useState<ClientReport | null>(null)
  const [reportError, setReportError] = useState<string | null>(null)

  const [forecast, setForecast] = useState<ForecastResult[] | null>(null)
  const [forecastError, setForecastError] = useState<string | null>(null)

  useEffect(() => {
    if (!workspaceId || !clientId) return
    getPortfolioReport(workspaceId)
      .then((reports) => {
        const clientPeriods = reports
          .filter((r) => r.client_id === clientId)
          .map((r) => r.period)
          .sort((a, b) => b.localeCompare(a))
        setPeriods(clientPeriods)
      })
      .catch((err) => setPeriodsError(err instanceof ApiError ? err.message : 'Could not load periods.'))
  }, [workspaceId, clientId])

  const period = periodParam ?? periods?.[0] ?? null

  useEffect(() => {
    if (!workspaceId || !clientId || !period) return
    getClientReport(workspaceId, clientId, period)
      .then(setReport)
      .catch((err) => setReportError(err instanceof ApiError ? err.message : 'Could not load the report.'))
  }, [workspaceId, clientId, period])

  useEffect(() => {
    if (!workspaceId || !clientId) return
    getClientForecast(workspaceId, clientId)
      .then(setForecast)
      .catch((err) =>
        setForecastError(err instanceof ApiError ? err.message : 'Could not load the forecast.'),
      )
  }, [workspaceId, clientId])

  if (!workspaceId || !clientId) {
    return <div className="p-8 text-sm text-red-600">Missing workspace or client in the URL.</div>
  }

  const tabItems: TabItem[] = TABS.map((t) => ({
    key: t.key,
    label: t.label,
    to: `/portfolio/${workspaceId}/clients/${clientId}/${t.key}${period ? `?period=${period}` : ''}`,
  }))

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <BackLink to={`/portfolio/${workspaceId}`}>Back to portfolio</BackLink>

      <div className="mt-2 flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-xl font-semibold text-slate-900 dark:text-slate-50">{clientId}</h1>

        <div className="flex items-center gap-3">
          {periods && periods.length > 0 && period && (
            <select
              value={period}
              onChange={(e) => setSearchParams({ period: e.target.value })}
              className="rounded-md border border-slate-300 bg-white px-2 py-1.5 text-sm text-slate-700 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
            >
              {periods.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
          )}
          {period && (
            <ButtonLink
              size="sm"
              href={`${API_BASE_URL}/workspaces/${workspaceId}/clients/${clientId}/report/pdf?${new URLSearchParams(
                { period, ...(getToken() ? { token: getToken()! } : {}) },
              )}`}
            >
              Download PDF report
            </ButtonLink>
          )}
        </div>
      </div>

      {periodsError && <p className="mt-4 text-sm text-red-600 dark:text-red-400">{periodsError}</p>}

      <div className="mt-4">
        <Tabs items={tabItems} active={activeTab} />
      </div>

      <div className="mt-6">
        {reportError && <p className="text-sm text-red-600 dark:text-red-400">{reportError}</p>}

        {activeTab === 'overview' && report && (
          <>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <KpiCard label="Revenue" value={report.actual_kpis.revenue} />
              <KpiCard
                label="Gross profit"
                value={report.actual_kpis.gross_profit}
                marginPct={report.actual_kpis.gross_margin_pct}
              />
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

            <div className="mt-8">
              <h3 className="mb-2 text-sm font-semibold text-slate-700 dark:text-slate-300">
                Needs attention
              </h3>
              {topMaterialVariances(report).length === 0 ? (
                <p className="text-sm text-slate-400">No material variances this period.</p>
              ) : (
                <ul className="space-y-2">
                  {topMaterialVariances(report).map((v) => (
                    <li
                      key={v.kpi_name + v.comparison_scenario}
                      className="flex items-start gap-3 rounded-lg border border-slate-200 bg-white p-3 dark:border-slate-700 dark:bg-slate-900"
                    >
                      <SeverityBadge severity={v.severity} />
                      <p className="text-sm text-slate-600 dark:text-slate-300">{v.narrative}</p>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </>
        )}

        {activeTab === 'variance' && report && (
          <div className="space-y-8">
            <VarianceTable title="Actual vs Budget" variances={report.variances_vs_budget} />
            <VarianceTable title="Actual vs Prior" variances={report.variances_vs_prior} />
          </div>
        )}

        {activeTab === 'forecast' && (
          <>
            {forecastError && <p className="text-sm text-slate-400">{forecastError}</p>}
            {forecast && <ForecastChart forecasts={forecast} />}
          </>
        )}

        {activeTab === 'aging-cash-flow' && (
          <div className="space-y-8">
            <AgingSection workspaceId={workspaceId} clientId={clientId} />
            <CashFlowChart workspaceId={workspaceId} clientId={clientId} />
          </div>
        )}
      </div>
    </div>
  )
}
