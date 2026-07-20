import { useState } from 'react'
import type { FormEvent } from 'react'
import { ApiError, getClientAging } from '../api/client'
import type { AgingReport } from '../types'
import { formatCurrency } from '../utils/format'
import { Button } from './ui/Button'
import { TextInput } from './ui/TextInput'
import { tableShell, tableHead, tableHeadCell, tableBody, tableCell, tableCellStrong } from './ui/table'

function AgingTable({ report }: { report: AgingReport }) {
  return (
    <div>
      <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-300">
        {report.type.toUpperCase()} · Total: {formatCurrency(report.total_outstanding)}
      </h4>
      <div className={`mt-2 ${tableShell}`}>
        <table className="w-full text-left text-sm">
          <thead className={tableHead}>
            <tr>
              <th className={tableHeadCell}>Bucket</th>
              <th className={tableHeadCell}>Amount</th>
              <th className={tableHeadCell}>Invoices</th>
            </tr>
          </thead>
          <tbody className={tableBody}>
            {report.buckets.map((b) => (
              <tr key={b.bucket}>
                <td className={tableCellStrong}>{b.bucket}</td>
                <td className={tableCell}>{formatCurrency(b.amount)}</td>
                <td className={tableCell}>{b.invoice_count}</td>
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
        setError('No AR or AP invoices on file for this client.')
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not calculate aging.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h3 className="mb-2 text-sm font-semibold text-slate-700 dark:text-slate-300">Aging AR/AP</h3>
      <form onSubmit={handleSubmit} className="flex flex-wrap items-end gap-3">
        <label className="text-sm text-slate-600 dark:text-slate-300">
          As-of date
          <TextInput type="date" value={asOf} onChange={(e) => setAsOf(e.target.value)} className="mt-1 block" />
        </label>
        <Button type="submit" size="sm" disabled={!asOf || loading}>
          {loading ? 'Calculating…' : 'View aging'}
        </Button>
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
