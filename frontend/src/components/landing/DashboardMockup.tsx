import { TrendingUp } from 'lucide-react'
import { CountUpNumber } from './CountUpNumber'

const SCENARIOS = [
  { label: 'Worst', value: 62, color: 'bg-slate-300 dark:bg-slate-700' },
  { label: 'Base', value: 84, color: 'bg-brand-400 dark:bg-brand-500' },
  { label: 'Best', value: 100, color: 'bg-accent-400' },
]

const ATTENTION_ROWS = [
  { client: 'Acme Consulting Ltd', period: '2026-06', severity: 'high' as const },
  { client: 'Meridian Logistics Ltd', period: '2026-06', severity: 'medium' as const },
]

const SEVERITY_DOT: Record<'high' | 'medium', string> = {
  high: 'bg-red-400',
  medium: 'bg-amber-400',
}

export function DashboardMockup() {
  return (
    <div
      aria-hidden="true"
      className="w-full max-w-md rounded-2xl border border-white/10 bg-brand-900/60 p-5 shadow-2xl shadow-brand-950/40 backdrop-blur"
    >
      <div className="flex items-center justify-between">
        <p className="text-xs font-medium text-brand-200">Client Portfolio · Illustrative</p>
        <TrendingUp className="h-4 w-4 text-accent-400" />
      </div>

      <div className="mt-4 grid grid-cols-3 gap-3">
        <div className="rounded-lg bg-white/5 p-3">
          <p className="text-[11px] text-brand-200">Revenue</p>
          <p className="mt-1 text-lg font-semibold text-white">
            <CountUpNumber value={188} prefix="£" suffix="k" />
          </p>
        </div>
        <div className="rounded-lg bg-white/5 p-3">
          <p className="text-[11px] text-brand-200">EBITDA margin</p>
          <p className="mt-1 text-lg font-semibold text-white">
            <CountUpNumber value={24} suffix="%" />
          </p>
        </div>
        <div className="rounded-lg bg-white/5 p-3">
          <p className="text-[11px] text-brand-200">vs. budget</p>
          <p className="mt-1 text-lg font-semibold text-accent-400">
            <CountUpNumber value={6} prefix="+" suffix="%" />
          </p>
        </div>
      </div>

      <div className="mt-4">
        <p className="text-[11px] text-brand-200">Forecast scenarios</p>
        <div className="mt-2 flex items-end gap-2">
          {SCENARIOS.map(({ label, value, color }) => (
            <div key={label} className="flex flex-1 flex-col items-center gap-1.5">
              <div className="flex h-16 w-full items-end rounded bg-white/5">
                <div className={`w-full rounded ${color}`} style={{ height: `${value}%` }} />
              </div>
              <span className="text-[10px] text-brand-200">{label}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="mt-4 space-y-1.5">
        <p className="text-[11px] text-brand-200">Needs attention</p>
        {ATTENTION_ROWS.map((row) => (
          <div
            key={row.client}
            className="flex items-center justify-between rounded-md bg-white/5 px-2.5 py-1.5 text-xs text-white"
          >
            <span>{row.client}</span>
            <span className={`h-1.5 w-1.5 rounded-full ${SEVERITY_DOT[row.severity]}`} />
          </div>
        ))}
      </div>
    </div>
  )
}
