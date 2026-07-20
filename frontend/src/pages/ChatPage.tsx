import { useState } from 'react'
import type { FormEvent } from 'react'
import { useParams } from 'react-router-dom'
import { Send } from 'lucide-react'
import { ApiError, chat } from '../api/client'
import { BackLink } from '../components/ui/BackLink'
import { Button } from '../components/ui/Button'
import { TextInput } from '../components/ui/TextInput'

interface DisplayMessage {
  role: 'user' | 'assistant'
  content: string
}

export function ChatPage() {
  const { workspaceId } = useParams<{ workspaceId: string }>()
  const [messages, setMessages] = useState<DisplayMessage[]>([])
  const [history, setHistory] = useState<unknown[]>([])
  const [input, setInput] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!input.trim() || !workspaceId) return

    const question = input.trim()
    setMessages((prev) => [...prev, { role: 'user', content: question }])
    setInput('')
    setError(null)
    setLoading(true)
    try {
      const result = await chat(workspaceId, question, history)
      setMessages((prev) => [...prev, { role: 'assistant', content: result.reply }])
      setHistory(result.history)
    } catch (err) {
      if (err instanceof ApiError && err.status === 503) {
        setError('El asistente conversacional todavía no está configurado (falta la API key del lado del servidor).')
      } else {
        setError(err instanceof ApiError ? err.message : 'No se pudo contactar al asistente.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mx-auto flex h-screen max-w-3xl flex-col px-4 py-8">
      <BackLink to={`/portfolio/${workspaceId}`}>Volver al portfolio</BackLink>
      <h1 className="mt-2 text-xl font-semibold text-slate-900 dark:text-slate-50">Analista FP&A</h1>
      <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
        Preguntale en lenguaje natural por KPIs, variance, forecast, aging o cash flow de cualquier cliente.
      </p>

      <div className="mt-6 flex-1 space-y-3 overflow-y-auto">
        {messages.map((m, i) => (
          <div
            key={i}
            className={`max-w-[80%] rounded-lg px-4 py-2 text-sm ${
              m.role === 'user'
                ? 'ml-auto bg-brand-600 text-white'
                : 'bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-100'
            }`}
          >
            {m.content}
          </div>
        ))}
        {loading && <p className="text-sm text-slate-400">Pensando…</p>}
      </div>

      {error && <p className="mt-3 text-sm text-red-600 dark:text-red-400">{error}</p>}

      <form onSubmit={handleSubmit} className="mt-4 flex gap-2">
        <TextInput
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="¿Cómo viene Beacon Partners este mes?"
          className="flex-1"
        />
        <Button type="submit" disabled={!input.trim() || loading}>
          <Send className="h-4 w-4" />
          Enviar
        </Button>
      </form>
    </div>
  )
}
