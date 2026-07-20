import { Link } from 'react-router-dom'
import { BarChart3, Bot, Cable, LineChart, ReceiptText } from 'lucide-react'
import { ButtonLink } from '../components/ui/Button'
import { Card } from '../components/ui/Card'

const FEATURES = [
  {
    icon: BarChart3,
    title: 'Automatic KPIs and variance',
    description: 'Revenue, EBITDA, margins and deviations vs. budget or prior period, by client and by period.',
  },
  {
    icon: LineChart,
    title: '3-scenario forecast',
    description: 'Best / base / worst projection for each client, generated from its own history.',
  },
  {
    icon: ReceiptText,
    title: 'AR/AP aging + cash flow',
    description: 'Overdue invoices by age and a weekly cash projection, no manual spreadsheets.',
  },
  {
    icon: Cable,
    title: 'Connected to Xero and QuickBooks',
    description: 'Sync P&L and invoices directly from each client’s accounting software.',
  },
  {
    icon: Bot,
    title: 'AI conversational assistant',
    description: 'Ask about any client in your portfolio in plain English and get a fast answer.',
  },
]

export function LandingPage() {
  return (
    <div className="min-h-screen bg-white dark:bg-slate-950">
      <header className="mx-auto flex max-w-5xl items-center justify-between px-4 py-6">
        <div className="flex items-center gap-2">
          <img src="/logo-mark-192.png" alt="" className="h-8 w-8" />
          <span translate="no" className="notranslate text-lg font-semibold text-brand-700 dark:text-brand-300">
            Alphatense
          </span>
        </div>
        <div className="flex items-center gap-4">
          <Link
            to="/login"
            className="text-sm font-medium text-slate-600 hover:text-brand-600 dark:text-slate-300 dark:hover:text-brand-400"
          >
            Log in
          </Link>
          <ButtonLink href="/signup" size="sm">
            Sign up
          </ButtonLink>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-4 pb-24 pt-12 text-center">
        <h1 className="mx-auto max-w-3xl text-4xl font-bold tracking-tight text-slate-900 dark:text-slate-50 sm:text-5xl">
          The FP&amp;A copilot for financial advisory firms
        </h1>
        <p className="mx-auto mt-5 max-w-2xl text-lg text-slate-600 dark:text-slate-400">
          A senior financial analyst available 24/7, on top of every client&apos;s accounting system — so your firm
          manages dozens of clients from a single dashboard, without building spreadsheets by hand.
        </p>
        <div className="mt-8 flex items-center justify-center gap-3">
          <ButtonLink href="/signup" size="md">
            Start for free
          </ButtonLink>
          <Link
            to="/login"
            className="inline-flex items-center justify-center rounded-md px-4 py-2 text-sm font-medium text-brand-700 hover:bg-brand-50 dark:text-brand-300 dark:hover:bg-slate-900"
          >
            I already have an account
          </Link>
        </div>

        <div className="mt-20 grid grid-cols-1 gap-4 text-left sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map(({ icon: Icon, title, description }) => (
            <Card key={title} className="p-5">
              <Icon className="h-6 w-6 text-brand-600 dark:text-brand-400" />
              <h3 className="mt-3 text-sm font-semibold text-slate-900 dark:text-slate-50">{title}</h3>
              <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{description}</p>
            </Card>
          ))}
        </div>
      </main>
    </div>
  )
}
