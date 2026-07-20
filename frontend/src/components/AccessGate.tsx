import { useState, type FormEvent, type ReactNode } from 'react'
import { API_BASE_URL, getAccessKey, setAccessKey } from '../api/client'
import { Button } from './ui/Button'
import { TextInput } from './ui/TextInput'

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
      <img src="/logo-mark-192.png" alt="Alphatense" className="h-16 w-16" />
      <h1 translate="no" className="notranslate text-lg font-semibold text-slate-900 dark:text-slate-50">
        Alphatense FP&A
      </h1>
      <p className="text-center text-sm text-slate-500 dark:text-slate-400">
        Ingresá el código de acceso para continuar.
      </p>
      <form className="flex w-full gap-2" onSubmit={handleSubmit}>
        <TextInput
          type="password"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Código de acceso"
          autoFocus
          className="flex-1"
        />
        <Button type="submit">Entrar</Button>
      </form>
    </div>
  )
}
