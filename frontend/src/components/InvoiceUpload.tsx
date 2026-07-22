import { useState } from 'react'
import type { FormEvent } from 'react'
import { FileCheck2, Paperclip } from 'lucide-react'
import { ApiError, uploadInvoices } from '../api/client'
import { Button } from './ui/Button'
import { Card } from './ui/Card'

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
      setStatus(`${invoices_loaded} invoices loaded.`)
      setFile(null)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not load the invoices.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card className="p-4">
      <form onSubmit={handleSubmit} className="flex flex-wrap items-center gap-3">
        <div>
          <p className="text-sm font-medium text-slate-700 dark:text-slate-200">AR/AP invoices (optional)</p>
          <p className="text-xs text-slate-400">Enables aging and cash flow per client.</p>
        </div>
        <label className="inline-flex cursor-pointer items-center gap-1.5 rounded-md border border-slate-300 px-3 py-1.5 text-sm text-slate-600 transition hover:border-brand-400 hover:text-brand-600 dark:border-slate-700 dark:text-slate-300 dark:hover:border-brand-500 dark:hover:text-brand-400">
          {file ? <FileCheck2 className="h-4 w-4 text-brand-600 dark:text-brand-400" /> : <Paperclip className="h-4 w-4" />}
          {file ? file.name : 'Choose file'}
          <input
            type="file"
            accept=".csv,.xlsx,.xls"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="sr-only"
          />
        </label>
        <Button type="submit" size="sm" disabled={!file || loading}>
          {loading ? 'Uploading…' : 'Upload invoices'}
        </Button>
        {status && <p className="text-sm text-emerald-600 dark:text-emerald-400">{status}</p>}
        {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
      </form>
    </Card>
  )
}
