import { useEffect, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { API_BASE_URL, ApiError, getClientForecast, getClientReport } from '../api/client'
import type { ClientReport, ForecastResult } from '../types'
import { KpiCard } from '../components/KpiCard'
import { VarianceTable } from '../components/VarianceTable'
import { ForecastChart } from '../components/ForecastChart'

export function ClientDetailPage() {
  const { workspaceId, clientId } = useParams<{ workspaceId: string; clientId: string }>()
  const [searchParams] = useSearchParams()
  const period = searchParams.get('period')

  const [report, setReport] = useState<ClientReport | null>(null)
  const [reportError, setReportError] = useState<string | null>(null)

  const [forecast, setForecast] = useState<ForecastResult[] | null>(null)
  const [forecastError, setForecastError] = useState<string | null>(null)

  useEffect(() => {
    if (!workspaceId || !clientId || !period) return
    getClientReport(workspaceId, clientId, period)
      .then(setReport)
      .catch((err) => setReportError(err instanceof ApiError ? err.message : 'No se pudo cargar el reporte.'))
  }, [workspaceId, clientId, period])

  useEffect(() => {
    if (!workspaceId || !clientId) return
    getClientForecast(workspaceId, clientId)
      .then(setForecast)
      .catch((err) =>
        setForecastError(err instanceof ApiError ? err.message : 'No se pudo cargar el forecast.'),
      )
  }, [workspaceId, clientId])

  if (!period) {
    return <div className="p-8 text-sm text-red-600">Falta el periodo en la URL.</div>
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <Link to={`/portfolio/${workspaceId}`} className="text-sm text-indigo-600 hover:underline">
        ← Volver al portfolio
      </Link>
      <div className="mt-2 flex items-center justify-between">
        <h1 className="text-xl font-semibold text-slate-900 dark:text-slate-50">
          {clientId} <span className="text-slate-400">· {period}</span>
        </h1>
        {workspaceId && clientId && period && (
          <a
            href={`${API_BASE_URL}/workspaces/${workspaceId}/clients/${clientId}/report/pdf?period=${period}`}
            className="rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700"
          >
            Descargar informe PDF
          </a>
        )}
      </div>

      {reportError && <p className="mt-4 text-sm text-red-600 dark:text-red-400">{reportError}</p>}

      {report && (
        <>
          <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
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

          <div className="mt-8 space-y-8">
            <VarianceTable title="Actual vs Budget" variances={report.variances_vs_budget} />
            <VarianceTable title="Actual vs Prior" variances={report.variances_vs_prior} />
          </div>
        </>
      )}

      <div className="mt-8">
        {forecastError && <p className="text-sm text-slate-400">{forecastError}</p>}
        {forecast && <ForecastChart forecasts={forecast} />}
      </div>
    </div>
  )
}
