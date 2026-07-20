import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { ForecastResult } from '../types'
import { formatCurrency } from '../utils/format'
import { Card } from './ui/Card'

const SCENARIO_COLORS = {
  best: '#059669',
  base: '#1b69b0',
  worst: '#dc2626',
}

interface ChartRow {
  period: string
  best?: number
  base?: number
  worst?: number
}

export function ForecastChart({ forecasts }: { forecasts: ForecastResult[] }) {
  if (forecasts.length === 0) {
    return <p className="text-sm text-slate-400">Not enough history to forecast this client.</p>
  }

  const byPeriod = new Map<string, ChartRow>()
  for (const f of forecasts) {
    const row = byPeriod.get(f.period) ?? { period: f.period }
    row[f.scenario] = f.net_income
    byPeriod.set(f.period, row)
  }
  const data = Array.from(byPeriod.values()).sort((a, b) => a.period.localeCompare(b.period))

  return (
    <div>
      <h3 className="mb-2 text-sm font-semibold text-slate-700 dark:text-slate-300">
        Net income forecast (best / base / worst)
      </h3>
      <Card className="h-72 w-full p-2">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-slate-200 dark:stroke-slate-700" />
            <XAxis dataKey="period" tick={{ fontSize: 12 }} />
            <YAxis tickFormatter={(v) => formatCurrency(v)} tick={{ fontSize: 11 }} width={90} />
            <Tooltip formatter={(v) => formatCurrency(Number(v))} />
            <Legend />
            <Line type="monotone" dataKey="best" name="Best" stroke={SCENARIO_COLORS.best} strokeWidth={2} />
            <Line type="monotone" dataKey="base" name="Base" stroke={SCENARIO_COLORS.base} strokeWidth={2} />
            <Line type="monotone" dataKey="worst" name="Worst" stroke={SCENARIO_COLORS.worst} strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </Card>
      <ul className="mt-3 space-y-1 text-xs text-slate-500 dark:text-slate-400">
        {forecasts
          .filter((f) => f.scenario === 'base')
          .map((f) => (
            <li key={f.period}>
              <span className="font-medium">{f.period}:</span> {f.assumptions}
            </li>
          ))}
      </ul>
    </div>
  )
}
