import { useState } from 'react'
import type { DragEvent } from 'react'
import { FileCheck2, UploadCloud } from 'lucide-react'

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export function UploadDropzone({
  file,
  onFileChange,
  accept = '.csv,.xlsx,.xls',
}: {
  file: File | null
  onFileChange: (file: File | null) => void
  accept?: string
}) {
  const [dragging, setDragging] = useState(false)

  function handleDrop(e: DragEvent<HTMLLabelElement>) {
    e.preventDefault()
    setDragging(false)
    const dropped = e.dataTransfer.files?.[0]
    if (dropped) onFileChange(dropped)
  }

  return (
    <label
      onDragOver={(e) => {
        e.preventDefault()
        setDragging(true)
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      className={`flex min-h-40 w-full cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed p-8 text-center transition ${
        dragging
          ? 'border-brand-500 bg-brand-50 dark:bg-brand-900/20'
          : 'border-slate-300 bg-slate-50 hover:border-brand-400 hover:bg-brand-50/50 dark:border-slate-700 dark:bg-slate-800/50 dark:hover:border-brand-500'
      }`}
    >
      <input
        type="file"
        accept={accept}
        onChange={(e) => onFileChange(e.target.files?.[0] ?? null)}
        className="sr-only"
      />
      {file ? (
        <>
          <FileCheck2 className="h-8 w-8 text-brand-600 dark:text-brand-400" />
          <p className="text-sm font-medium text-slate-800 dark:text-slate-100">{file.name}</p>
          <p className="text-xs text-slate-500 dark:text-slate-400">{formatFileSize(file.size)} · selected</p>
          <span className="mt-1 text-xs text-brand-600 underline dark:text-brand-400">Change file</span>
        </>
      ) : (
        <>
          <UploadCloud className="h-8 w-8 text-slate-400" />
          <p className="text-sm font-medium text-slate-700 dark:text-slate-200">
            Drag and drop your file here, or click to browse
          </p>
          <p className="text-xs text-slate-400">CSV or Excel (.csv, .xlsx, .xls)</p>
        </>
      )}
    </label>
  )
}
