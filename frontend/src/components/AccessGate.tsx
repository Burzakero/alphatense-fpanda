import { useState, type FormEvent, type ReactNode } from 'react'
import { API_BASE_URL, getAccessKey, setAccessKey } from '../api/client'

const IS_LOCAL_DEV = /^https?:\/\/(localhost|127\.0\.0\.1)/.test(API_BASE_URL)

export function AccessGate({ children }: { children: ReactNode }) {
  const [unlocked, setUnlocked] = useState(() => IS_LOCAL_DEV || Boolean(getAccessKey()))
  const [input, setInput] = useState('')

  if (unlocked) return <>{children}</>

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!input.trim()) return
    setAccessKey(input.trim())
    setUnlocked(true)
  }

  return (
    <div className="mx-auto flex min-h-screen max-w-sm flex-col items-center justify-center gap-4 px-4">
      <h1 className="text-lg font-semibold text-slate-900 dark:text-slate-50">Alphatense FP&A</h1>
      <p className="text-center text-sm text-slate-500 dark:text-slate-400">
        Ingresá el código de acceso para continuar.
      </p>
      <form className="flex w-full gap-2" onSubmit={handleSubmit}>
        <input
          type="password"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Código de acceso"
          autoFocus
          className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100"
        />
        <button
          type="submit"
          className="rounded-md bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700"
        >
          Entrar
        </button>
      </form>
    </div>
  )
}
