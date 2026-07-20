import { useState } from 'react'
import type { FormEvent } from 'react'
import { ApiError, uploadInvoices } from '../api/client'
import { Button } from './ui/Button'

export function InvoiceUpload({ workspaceId }: { workspaceId: string }) {
  const [file, setFile] = useState<File | null>(null)
  const [status, setStatus] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!file) return
    setError(null)
    setStatus(null)
    setLoading(true)
    try {
      const { invoices_loaded } = await uploadInvoices(workspaceId, file)
      setStatus(`${invoices_loaded} facturas cargadas.`)
      setFile(null)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudieron cargar las facturas.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="flex flex-wrap items-center gap-3 rounded-lg border border-dashed border-slate-300 bg-white p-4 dark:border-slate-700 dark:bg-slate-900"
    >
      <div>
        <p className="text-sm font-medium text-slate-700 dark:text-slate-200">Facturas AR/AP (opcional)</p>
        <p className="text-xs text-slate-400">Habilita aging y cash flow por cliente.</p>
      </div>
      <input
        type="file"
        accept=".csv,.xlsx,.xls"
        onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        className="text-sm text-slate-600 dark:text-slate-300"
      />
      <Button type="submit" size="sm" disabled={!file || loading}>
        {loading ? 'Subiendo…' : 'Subir facturas'}
      </Button>
      {status && <p className="text-sm text-emerald-600 dark:text-emerald-400">{status}</p>}
      {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
    </form>
  )
}
