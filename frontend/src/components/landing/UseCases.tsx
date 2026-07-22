import { useInView } from '../../hooks/useInView'
import { CountUpNumber } from './CountUpNumber'

// Illustrative scenarios describing what the product automates — Alphatense is in
// early pilot validation, so these are not yet audited results from real customers.
const USE_CASES = [
  {
    value: 92,
    suffix: '%',
    label: 'Faster monthly close',
    description:
      'A 40-client advisory firm cuts its consolidated monthly close from 5 days to under 4 hours by automating KPI and variance calculations across every client.',
  },
  {
    value: 12,
    suffix: 'h',
    label: 'Saved per analyst, per week',
    description:
      'No more rebuilding the same variance spreadsheet for each client — KPIs and forecasts recalculate automatically on every data refresh.',
  },
  {
    value: 100,
    suffix: '%',
    label: 'Of the portfolio reviewed weekly',
    description:
      'Instead of spot-checking a handful of accounts, advisors get a single "needs attention" view across their entire client base, every week.',
  },
]

export function UseCases() {
  const { ref, inView } = useInView<HTMLDivElement>()

  return (
    <section id="use-cases" className="scroll-mt-20 bg-white py-24 dark:bg-slate-950">
      <div
        ref={ref}
        className={`mx-auto max-w-6xl px-4 transition-all duration-700 ease-out ${
          inView ? 'translate-y-0 opacity-100' : 'translate-y-4 opacity-0'
        }`}
      >
        <h2 className="text-center text-3xl font-bold tracking-tight text-slate-900 dark:text-slate-50">
          What this looks like in practice
        </h2>
        <p className="mx-auto mt-3 max-w-xl text-center text-slate-500 dark:text-slate-400">
          Illustrative scenarios based on the workflows Alphatense automates — we&apos;re in early pilot validation
          with advisory firms.
        </p>

        <div className="mt-12 grid grid-cols-1 gap-6 sm:grid-cols-3">
          {USE_CASES.map(({ value, suffix, label, description }) => (
            <div
              key={label}
              className="rounded-xl border border-slate-200 bg-white p-6 text-left shadow-sm dark:border-slate-800 dark:bg-slate-900"
            >
              <p className="text-4xl font-bold tracking-tight text-brand-600 dark:text-brand-400">
                <CountUpNumber value={value} suffix={suffix} />
              </p>
              <h3 className="mt-2 text-sm font-semibold text-slate-900 dark:text-slate-50">{label}</h3>
              <p className="mt-1.5 text-sm text-slate-500 dark:text-slate-400">{description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
