import { useState } from 'react'
import type { FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { ApiError, createWorkspace } from '../api/client'
import { Button } from '../components/ui/Button'
import { PageHeading } from '../components/ui/PageHeading'

export function UploadPage() {
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
        title="Upload your portfolio"
        subtitle="Upload your portfolio's CSV/Excel to see KPIs, variance analysis and forecast."
      />

      <form
        onSubmit={handleSubmit}
        className="w-full rounded-lg border border-dashed border-slate-300 bg-white p-8 text-center dark:border-slate-700 dark:bg-slate-900"
      >
        <input
          type="file"
          accept=".csv,.xlsx,.xls"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          className="mx-auto block text-sm text-slate-600 dark:text-slate-300"
        />
        <Button type="submit" disabled={!file || loading} className="mt-4">
          {loading ? 'Uploading…' : 'Upload and view portfolio'}
        </Button>
        {error && <p className="mt-3 text-sm text-red-600 dark:text-red-400">{error}</p>}
      </form>

      <p className="text-xs text-slate-400">
        Expected columns: client_id, period, scenario, account, category, amount
      </p>
    </div>
  )
}
