import { useState } from 'react'
import { BarChart3, Bot, Cable, LineChart, ReceiptText } from 'lucide-react'
import { useInView } from '../../hooks/useInView'

const FEATURES = [
  {
    number: '01',
    icon: BarChart3,
    title: 'Automatic KPIs and variance',
    description: 'Revenue, EBITDA, margins and deviations vs. budget or prior period, by client and by period.',
  },
  {
    number: '02',
    icon: LineChart,
    title: '3-scenario forecast',
    description: 'Best / base / worst projection for each client, generated from its own history.',
  },
  {
    number: '03',
    icon: ReceiptText,
    title: 'AR/AP aging + cash flow',
    description: 'Overdue invoices by age and a weekly cash projection, no manual spreadsheets.',
  },
  {
    number: '04',
    icon: Cable,
    title: 'Connected to Xero and QuickBooks',
    description: 'Sync P&L and invoices directly from each client’s accounting software.',
  },
  {
    number: '05',
    icon: Bot,
    title: 'AI conversational assistant',
    description: 'Ask about any client in your portfolio in plain English and get a fast answer.',
  },
]

export function FeaturesGrid() {
  const { ref, inView } = useInView<HTMLDivElement>()
  const [hovered, setHovered] = useState<string | null>(null)

  return (
    <section id="capabilities" className="scroll-mt-20 bg-white py-24 dark:bg-slate-950">
      <div
        ref={ref}
        className={`mx-auto max-w-6xl px-4 transition-all duration-700 ease-out ${
          inView ? 'translate-y-0 opacity-100' : 'translate-y-4 opacity-0'
        }`}
      >
        <h2 className="text-center text-3xl font-bold tracking-tight text-slate-900 dark:text-slate-50">
          What&apos;s included
        </h2>
        <p className="mx-auto mt-3 max-w-xl text-center text-slate-500 dark:text-slate-400">
          One platform covering the full FP&amp;A workflow for every client in your portfolio.
        </p>

        <div className="mt-12 grid grid-cols-1 gap-px overflow-hidden rounded-xl border border-slate-200 bg-slate-200 sm:grid-cols-2 lg:grid-cols-3 dark:border-slate-800 dark:bg-slate-800">
          {FEATURES.map(({ number, icon: Icon, title, description }) => {
            const isHovered = hovered === number
            const isDimmed = hovered !== null && !isHovered
            return (
              <div
                key={number}
                onMouseEnter={() => setHovered(number)}
                onMouseLeave={() => setHovered(null)}
                className={`bg-white p-6 transition duration-200 dark:bg-slate-950 ${
                  isHovered ? 'relative z-10 ring-2 ring-inset ring-brand-500' : ''
                } ${isDimmed ? 'opacity-60' : 'opacity-100'}`}
              >
                <span className="text-sm font-semibold tabular-nums text-brand-500">{number}</span>
                <Icon className="mt-3 h-6 w-6 text-brand-600 dark:text-brand-400" strokeWidth={1.5} />
                <h3 className="mt-3 text-sm font-semibold text-slate-900 dark:text-slate-50">{title}</h3>
                <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{description}</p>
              </div>
            )
          })}
        </div>
      </div>
    </section>
  )
}
