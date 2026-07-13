import { useState } from 'react'
import type { FormEvent } from 'react'
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { ApiError, getClientCashFlow } from '../api/client'
import type { CashFlowForecast } from '../types'
import { formatCurrency } from '../utils/format'

export function CashFlowChart({ workspaceId, clientId }: { workspaceId: string; clientId: string }) {
  const [asOf, setAsOf] = useState('')
  const [startingBalance, setStartingBalance] = useState('')
  const [forecast, setForecast] = useState<CashFlowForecast | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!asOf || !startingBalance) return
    setError(null)
    setLoading(true)
    try {
      const result = await getClientCashFlow(workspaceId, clientId, Number(startingBalance), asOf)
      setForecast(result)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo proyectar el cash flow.')
    } finally {
      setLoading(false)
    }
  }

  const data = forecast?.weeks.map((w) => ({ week: w.week_start, balance: w.ending_balance })) ?? []

  return (
    <div>
      <h3 className="mb-2 text-sm font-semibold text-slate-700 dark:text-slate-300">Cash Flow Proyectado</h3>
      <form onSubmit={handleSubmit} className="flex flex-wrap items-end gap-3">
        <label className="text-sm text-slate-600 dark:text-slate-300">
          Fecha de partida
          <input
            type="date"
            value={asOf}
            onChange={(e) => setAsOf(e.target.value)}
            className="mt-1 block rounded-md border border-slate-300 px-2 py-1 text-sm dark:border-slate-700 dark:bg-slate-800"
          />
        </label>
        <label className="text-sm text-slate-600 dark:text-slate-300">
          Balance inicial
          <input
            type="number"
            value={startingBalance}
            onChange={(e) => setStartingBalance(e.target.value)}
            placeholder="10000"
            className="mt-1 block w-32 rounded-md border border-slate-300 px-2 py-1 text-sm dark:border-slate-700 dark:bg-slate-800"
          />
        </label>
        <button
          type="submit"
          disabled={!asOf || !startingBalance || loading}
          className="rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-40"
        >
          {loading ? 'Proyectando…' : 'Ver cash flow'}
        </button>
      </form>

      {error && <p className="mt-3 text-sm text-red-600 dark:text-red-400">{error}</p>}

      {forecast && (
        <div className="mt-4">
          <div className="h-64 w-full rounded-lg border border-slate-200 bg-white p-2 dark:border-slate-700 dark:bg-slate-900">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-slate-200 dark:stroke-slate-700" />
                <XAxis dataKey="week" tick={{ fontSize: 11 }} />
                <YAxis tickFormatter={(v) => formatCurrency(v)} tick={{ fontSize: 11 }} width={90} />
                <Tooltip formatter={(v) => formatCurrency(Number(v))} />
                <Line type="monotone" dataKey="balance" name="Balance" stroke="#2563eb" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">{forecast.narrative}</p>
        </div>
      )}
    </div>
  )
}
