import { useState } from 'react'
import type { FormEvent } from 'react'
import { ApiError, getClientAging } from '../api/client'
import type { AgingReport } from '../types'
import { formatCurrency } from '../utils/format'

function AgingTable({ report }: { report: AgingReport }) {
  return (
    <div>
      <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-300">
        {report.type.toUpperCase()} · Total: {formatCurrency(report.total_outstanding)}
      </h4>
      <div className="mt-2 overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-700">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-50 text-slate-500 dark:bg-slate-800 dark:text-slate-400">
            <tr>
              <th className="px-3 py-2 font-medium">Bucket</th>
              <th className="px-3 py-2 font-medium">Monto</th>
              <th className="px-3 py-2 font-medium">Facturas</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {report.buckets.map((b) => (
              <tr key={b.bucket}>
                <td className="px-3 py-2 text-slate-800 dark:text-slate-200">{b.bucket}</td>
                <td className="px-3 py-2 text-slate-600 dark:text-slate-300">{formatCurrency(b.amount)}</td>
                <td className="px-3 py-2 text-slate-600 dark:text-slate-300">{b.invoice_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">{report.narrative}</p>
    </div>
  )
}

export function AgingSection({ workspaceId, clientId }: { workspaceId: string; clientId: string }) {
  const [asOf, setAsOf] = useState('')
  const [reports, setReports] = useState<AgingReport[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!asOf) return
    setError(null)
    setLoading(true)
    try {
      const results = await Promise.allSettled([
        getClientAging(workspaceId, clientId, 'ar', asOf),
        getClientAging(workspaceId, clientId, 'ap', asOf),
      ])
      const ok = results
        .filter((r): r is PromiseFulfilledResult<AgingReport> => r.status === 'fulfilled')
        .map((r) => r.value)
      setReports(ok)
      if (ok.length === 0) {
        setError('No hay facturas AR ni AP cargadas para este cliente.')
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo calcular el aging.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h3 className="mb-2 text-sm font-semibold text-slate-700 dark:text-slate-300">Aging AR/AP</h3>
      <form onSubmit={handleSubmit} className="flex flex-wrap items-end gap-3">
        <label className="text-sm text-slate-600 dark:text-slate-300">
          Fecha de corte
          <input
            type="date"
            value={asOf}
            onChange={(e) => setAsOf(e.target.value)}
            className="mt-1 block rounded-md border border-slate-300 px-2 py-1 text-sm dark:border-slate-700 dark:bg-slate-800"
          />
        </label>
        <button
          type="submit"
          disabled={!asOf || loading}
          className="rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-40"
        >
          {loading ? 'Calculando…' : 'Ver aging'}
        </button>
      </form>

      {error && <p className="mt-3 text-sm text-red-600 dark:text-red-400">{error}</p>}

      {reports && reports.length > 0 && (
        <div className="mt-4 space-y-6">
          {reports.map((r) => (
            <AgingTable key={r.type} report={r} />
          ))}
        </div>
      )}
    </div>
  )
}
