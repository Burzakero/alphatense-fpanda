import { useState } from 'react'
import type { FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { ApiError, createWorkspace } from '../api/client'
import { Button } from '../components/ui/Button'

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
      setError(err instanceof ApiError ? err.message : 'No se pudo subir el archivo.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mx-auto flex min-h-screen max-w-xl flex-col items-center justify-center gap-6 px-4">
      <div className="flex flex-col items-center text-center">
        <img src="/logo-mark-192.png" alt="" className="mb-3 h-16 w-16" />
        <h1 translate="no" className="notranslate text-2xl font-semibold text-slate-900 dark:text-slate-50">
          Alphatense FP&A
        </h1>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
          Subí el CSV/Excel de tu portfolio para ver KPIs, variance analysis y forecast.
        </p>
      </div>

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
          {loading ? 'Subiendo…' : 'Subir y ver portfolio'}
        </Button>
        {error && <p className="mt-3 text-sm text-red-600 dark:text-red-400">{error}</p>}
      </form>

      <p className="text-xs text-slate-400">
        Columnas esperadas: client_id, period, scenario, account, category, amount
      </p>
    </div>
  )
}
