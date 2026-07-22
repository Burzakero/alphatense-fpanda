import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Download, MessageCircle, Upload } from 'lucide-react'
import { ApiError, createWorkspace, getPortfolioReport } from '../api/client'
import { useAuth } from '../auth/context'
import type { ClientReport } from '../types'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { PageHeading } from '../components/ui/PageHeading'
import { SeverityBadge } from '../components/SeverityBadge'
import { UploadDropzone } from '../components/UploadDropzone'

const LINK_BUTTON =
  'inline-flex items-center justify-center gap-2 rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-brand-700'
const LINK_BUTTON_SM =
  'inline-flex items-center justify-center gap-2 rounded-md bg-slate-600 px-3 py-1.5 text-sm font-medium text-white transition hover:bg-slate-700'

function GetStarted() {
  const { refresh } = useAuth()
  const [file, setFile] = useState<File | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!file) return
    setError(null)
    setLoading(true)
    try {
      const { workspace_id } = await createWorkspace(file)
      await refresh()
      navigate(`/portfolio/${workspace_id}`)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not upload the file.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mx-auto flex max-w-xl flex-col gap-6 px-4 py-16">
      <PageHeading
        title="Welcome to Alphatense"
        subtitle="Let's load your first portfolio. Three steps: upload your data, we calculate KPIs, variance and forecast, then review it with your AI analyst."
      />
      <form onSubmit={handleSubmit} className="flex w-full flex-col items-center gap-4">
        <UploadDropzone file={file} onFileChange={setFile} />
        <Button type="submit" disabled={!file || loading}>
          {loading ? 'Uploading…' : 'Upload and view portfolio'}
        </Button>
        {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
      </form>
      <p className="text-center text-xs text-slate-400">
        Expected columns: client_id, period, scenario, account, category, amount
      </p>
      <a
        href="/alphatense-sample-template.xlsx"
        download
        className="inline-flex items-center justify-center gap-2 text-sm font-medium text-brand-600 hover:underline dark:text-brand-400"
      >
        <Download className="h-4 w-4" />
        Download sample template (.xlsx)
      </a>
    </div>
  )
}

function StatCard({ label, value }: { label: string; value: number }) {
  return (
    <Card className="p-4">
      <p className="text-sm text-slate-500 dark:text-slate-400">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-slate-900 dark:text-slate-50">{value}</p>
    </Card>
  )
}

function Dashboard({ workspaceId }: { workspaceId: string }) {
  const { advisor } = useAuth()
  const [reports, setReports] = useState<ClientReport[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getPortfolioReport(workspaceId)
      .then(setReports)
      .catch((err) => setError(err instanceof ApiError ? err.message : 'Could not load the portfolio.'))
  }, [workspaceId])

  if (error) {
    return <div className="p-8 text-sm text-red-600 dark:text-red-400">{error}</div>
  }

  if (!reports) {
    return <div className="p-8 text-sm text-slate-500">Loading your dashboard…</div>
  }

  const clientCount = new Set(reports.map((r) => r.client_id)).size
  const needsAttention = reports
    .map((report) => ({
      report,
      variances: [...report.variances_vs_budget, ...report.variances_vs_prior].filter(
        (v) => v.severity !== 'low',
      ),
    }))
    .filter((r) => r.variances.length > 0)
    .slice(0, 5)

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <PageHeading
        title={`Welcome back, ${advisor.name}`}
        subtitle={`${reports.length} client/period report${reports.length === 1 ? '' : 's'} across your portfolio.`}
        action={
          <div className="flex items-center gap-3">
            <Link
              to={`/portfolio/${workspaceId}/chat`}
              className="inline-flex items-center gap-1.5 text-sm text-brand-600 hover:underline dark:text-brand-400"
            >
              <MessageCircle className="h-4 w-4" />
              Ask the AI analyst
            </Link>
            <Link to="/upload" className={LINK_BUTTON_SM}>
              <Upload className="h-4 w-4" />
              Upload more data
            </Link>
          </div>
        }
      />

      <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatCard label="Clients" value={clientCount} />
        <StatCard label="Reports" value={reports.length} />
        <StatCard label="Needs attention" value={needsAttention.length} />
        <StatCard label="No material variance" value={reports.length - needsAttention.length} />
      </div>

      <div className="mt-8">
        <h2 className="mb-3 text-sm font-semibold text-slate-700 dark:text-slate-300">Needs attention</h2>
        {needsAttention.length === 0 ? (
          <Card className="p-4 text-sm text-slate-500 dark:text-slate-400">
            No material variances across your portfolio right now.
          </Card>
        ) : (
          <div className="space-y-3">
            {needsAttention.map(({ report, variances }) => (
              <Link
                key={`${report.client_id}-${report.period}`}
                to={`/portfolio/${workspaceId}/clients/${report.client_id}?period=${report.period}`}
                className="flex items-center justify-between rounded-lg border border-slate-200 bg-white p-4 shadow-sm transition hover:border-brand-400 dark:border-slate-700 dark:bg-slate-900"
              >
                <span className="font-medium text-slate-800 dark:text-slate-100">
                  {report.client_id} <span className="text-slate-400">· {report.period}</span>
                </span>
                <div className="flex items-center gap-2">
                  {variances.map((v) => (
                    <SeverityBadge key={v.kpi_name + v.comparison_scenario} severity={v.severity} />
                  ))}
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>

      <div className="mt-8">
        <Link to={`/portfolio/${workspaceId}`} className={LINK_BUTTON}>
          View full portfolio
        </Link>
      </div>
    </div>
  )
}

export function HomePage() {
  const { workspaceIds } = useAuth()
  if (workspaceIds.length === 0) return <GetStarted />
  return <Dashboard workspaceId={workspaceIds[0]} />
}
