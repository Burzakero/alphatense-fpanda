import { Cable, MessageSquareText, Sparkles, FileOutput } from 'lucide-react'
import { useInView } from '../../hooks/useInView'

const STEPS = [
  {
    number: '1',
    icon: Cable,
    title: 'Connect your clients',
    description: 'Sync Xero or QuickBooks, or upload a spreadsheet for each client in your portfolio.',
  },
  {
    number: '2',
    icon: Sparkles,
    title: 'The engine calculates',
    description: 'KPIs, variance vs. budget or prior period, and a 3-scenario forecast — computed automatically.',
  },
  {
    number: '3',
    icon: MessageSquareText,
    title: 'Your AI analyst narrates it',
    description: 'Plain-English commentary on what changed for each client and why it matters.',
  },
  {
    number: '4',
    icon: FileOutput,
    title: 'Export or ask',
    description: 'Download an executive PDF report, or ask follow-up questions in the chat.',
  },
]

export function HowItWorks() {
  const { ref, inView } = useInView<HTMLDivElement>()

  return (
    <section id="how-it-works" className="scroll-mt-20 bg-slate-50 py-24 dark:bg-slate-900/40">
      <div
        ref={ref}
        className={`mx-auto max-w-6xl px-4 transition-all duration-700 ease-out ${
          inView ? 'translate-y-0 opacity-100' : 'translate-y-4 opacity-0'
        }`}
      >
        <h2 className="text-center text-3xl font-bold tracking-tight text-slate-900 dark:text-slate-50">
          How it works
        </h2>

        <div className="mt-14 grid grid-cols-1 gap-10 sm:grid-cols-2 lg:grid-cols-4">
          {STEPS.map(({ number, icon: Icon, title, description }, index) => (
            <div key={number} className="relative text-left">
              {index < STEPS.length - 1 && (
                <div
                  aria-hidden="true"
                  className="absolute top-6 left-full hidden h-px w-10 bg-slate-300 lg:block dark:bg-slate-700"
                />
              )}
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-brand-600 text-white">
                <Icon className="h-5 w-5" strokeWidth={1.75} />
              </div>
              <p className="mt-4 text-xs font-semibold tabular-nums text-brand-500">STEP {number}</p>
              <h3 className="mt-1 text-base font-semibold text-slate-900 dark:text-slate-50">{title}</h3>
              <p className="mt-1.5 text-sm text-slate-500 dark:text-slate-400">{description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
