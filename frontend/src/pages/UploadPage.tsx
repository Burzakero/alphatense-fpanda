import { useState } from 'react'
import type { FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { Download } from 'lucide-react'
import { ApiError, createWorkspace } from '../api/client'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { PageHeading } from '../components/ui/PageHeading'
import { UploadDropzone } from '../components/UploadDropzone'

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

      <Card className="flex w-full flex-col items-center gap-4 p-6">
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
          className="inline-flex items-center gap-2 text-sm font-medium text-brand-600 hover:underline dark:text-brand-400"
        >
          <Download className="h-4 w-4" />
          Download sample template (.xlsx)
        </a>
      </Card>
    </div>
  )
}
