import { Link } from 'react-router-dom'
import { BarChart3, Bot, Cable, Lock, Play, ReceiptText, ShieldCheck, LineChart } from 'lucide-react'
import { ButtonLink } from '../components/ui/Button'
import { Card } from '../components/ui/Card'

const CONTACT_EMAIL = 'hello@alphatense.com'

const STEPS = [
  {
    number: '1',
    title: 'Connect your clients',
    description: 'Sync Xero or QuickBooks, or upload a spreadsheet for each client in your portfolio.',
  },
  {
    number: '2',
    title: 'We do the analysis',
    description: 'KPIs, variance vs. budget or prior period, and a 3-scenario forecast — calculated automatically.',
  },
  {
    number: '3',
    title: 'Review with your AI analyst',
    description: 'Ask questions in plain English and export an executive PDF report for each client.',
  },
]

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

const TRUST_POINTS = [
  {
    icon: Lock,
    text: 'Bank-level encryption for data in transit and at rest',
  },
  {
    icon: ShieldCheck,
    text: "Each firm's client data is fully isolated — never shared across accounts",
  },
  {
    icon: Cable,
    text: 'Built on the official Xero and QuickBooks APIs',
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
          Purpose-built AI for financial advisory workflows — KPIs, variance and forecasts for every client,
          without building spreadsheets by hand.
        </p>
        <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
          <ButtonLink href="/signup" size="md">
            Start for free
          </ButtonLink>
          <a
            href={`mailto:${CONTACT_EMAIL}?subject=${encodeURIComponent('Alphatense demo request')}`}
            className="inline-flex items-center justify-center rounded-md border border-brand-600 px-4 py-2 text-sm font-medium text-brand-700 transition hover:bg-brand-50 dark:border-brand-400 dark:text-brand-300 dark:hover:bg-slate-900"
          >
            Book a 15-min demo
          </a>
        </div>
        <Link
          to="/login"
          className="mt-3 inline-block text-sm font-medium text-brand-700 hover:underline dark:text-brand-300"
        >
          I already have an account
        </Link>

        <div className="mx-auto mt-12 max-w-3xl">
          <div className="flex aspect-video items-center justify-center rounded-xl border border-dashed border-slate-300 bg-slate-100 dark:border-slate-700 dark:bg-slate-900">
            <div className="flex flex-col items-center gap-2 text-slate-400 dark:text-slate-500">
              <Play className="h-10 w-10" />
              <span className="text-sm font-medium">Product demo — 2 min</span>
            </div>
          </div>
        </div>

        <section className="mt-24">
          <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-50">How it works</h2>
          <div className="mt-8 grid grid-cols-1 gap-6 text-left sm:grid-cols-3">
            {STEPS.map(({ number, title, description }) => (
              <div key={number}>
                <span className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-600 text-sm font-semibold text-white">
                  {number}
                </span>
                <h3 className="mt-3 text-sm font-semibold text-slate-900 dark:text-slate-50">{title}</h3>
                <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{description}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="mt-24">
          <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-50">What&apos;s included</h2>
          <div className="mt-8 grid grid-cols-1 gap-4 text-left sm:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map(({ icon: Icon, title, description }) => (
              <Card key={title} className="p-5">
                <Icon className="h-6 w-6 text-brand-600 dark:text-brand-400" />
                <h3 className="mt-3 text-sm font-semibold text-slate-900 dark:text-slate-50">{title}</h3>
                <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{description}</p>
              </Card>
            ))}
          </div>
        </section>

        <section className="mt-24 border-y border-slate-200 py-8 dark:border-slate-800">
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-3">
            {TRUST_POINTS.map(({ icon: Icon, text }) => (
              <div key={text} className="flex flex-col items-center gap-2 text-center">
                <Icon className="h-5 w-5 text-brand-600 dark:text-brand-400" />
                <p className="text-sm text-slate-600 dark:text-slate-400">{text}</p>
              </div>
            ))}
          </div>
        </section>
      </main>

      <footer className="px-4 py-8">
        <div className="mx-auto flex max-w-5xl flex-col items-center justify-between gap-4 text-sm text-slate-500 dark:text-slate-400 sm:flex-row">
          <div className="flex items-center gap-2">
            <img src="/logo-mark-192.png" alt="" className="h-5 w-5" />
            <span translate="no" className="notranslate">
              © {new Date().getFullYear()} Alphatense
            </span>
          </div>
          <a href={`mailto:${CONTACT_EMAIL}`} className="hover:text-brand-600 dark:hover:text-brand-400">
            {CONTACT_EMAIL}
          </a>
        </div>
      </footer>
    </div>
  )
}
