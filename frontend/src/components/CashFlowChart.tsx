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
import { Button } from './ui/Button'
import { TextInput } from './ui/TextInput'
import { Card } from './ui/Card'

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
      setError(err instanceof ApiError ? err.message : 'Could not project cash flow.')
    } finally {
      setLoading(false)
    }
  }

  const data = forecast?.weeks.map((w) => ({ week: w.week_start, balance: w.ending_balance })) ?? []

  return (
    <div>
      <h3 className="mb-2 text-sm font-semibold text-slate-700 dark:text-slate-300">Projected Cash Flow</h3>
      <form onSubmit={handleSubmit} className="flex flex-wrap items-end gap-3">
        <label className="text-sm text-slate-600 dark:text-slate-300">
          Starting date
          <TextInput
            type="date"
            value={asOf}
            onChange={(e) => setAsOf(e.target.value)}
            className="mt-1 block"
          />
        </label>
        <label className="text-sm text-slate-600 dark:text-slate-300">
          Starting balance
          <TextInput
            type="number"
            value={startingBalance}
            onChange={(e) => setStartingBalance(e.target.value)}
            placeholder="10000"
            className="mt-1 block w-32"
          />
        </label>
        <Button type="submit" size="sm" disabled={!asOf || !startingBalance || loading}>
          {loading ? 'Projecting…' : 'View cash flow'}
        </Button>
      </form>

      {error && <p className="mt-3 text-sm text-red-600 dark:text-red-400">{error}</p>}

      {forecast && (
        <div className="mt-4">
          <Card className="h-64 w-full p-2">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-slate-200 dark:stroke-slate-700" />
                <XAxis dataKey="week" tick={{ fontSize: 11 }} />
                <YAxis tickFormatter={(v) => formatCurrency(v)} tick={{ fontSize: 11 }} width={90} />
                <Tooltip formatter={(v) => formatCurrency(Number(v))} />
                <Line type="monotone" dataKey="balance" name="Balance" stroke="#1b69b0" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </Card>
          <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">{forecast.narrative}</p>
        </div>
      )}
    </div>
  )
}
