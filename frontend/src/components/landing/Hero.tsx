import { ButtonLink } from '../ui/Button'
import { CONTACT_EMAIL } from '../../constants'
import { useInView } from '../../hooks/useInView'
import { DashboardMockup } from './DashboardMockup'

export function Hero() {
  const { ref, inView } = useInView<HTMLDivElement>()

  return (
    <section className="relative overflow-hidden bg-brand-950">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-brand-800/40 via-brand-950 to-brand-950"
      />
      <div className="relative mx-auto grid max-w-6xl gap-12 px-4 py-20 md:grid-cols-2 md:items-center md:py-28">
        <div
          ref={ref}
          className={`transition-all duration-700 ease-out ${
            inView ? 'translate-y-0 opacity-100' : 'translate-y-4 opacity-0'
          }`}
        >
          <h1 className="max-w-xl text-4xl font-bold tracking-tight text-white sm:text-5xl">
            The FP&amp;A copilot for financial advisory firms
          </h1>
          <p className="mt-5 max-w-lg text-lg text-slate-300">
            Purpose-built AI for financial advisory workflows, integrated directly on top of your clients&apos;
            existing ERP or spreadsheets — no data migration required.
          </p>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <ButtonLink href="/signup" size="md" className="shadow-lg shadow-brand-900/40 hover:scale-[1.02]">
              Start for free
            </ButtonLink>
            <a
              href={`mailto:${CONTACT_EMAIL}?subject=${encodeURIComponent('Alphatense demo request')}`}
              className="inline-flex items-center justify-center rounded-md border border-white/20 px-4 py-2 text-sm font-medium text-white transition hover:scale-[1.02] hover:border-white/40 hover:bg-white/5"
            >
              Talk to sales
            </a>
          </div>
        </div>

        <div className="flex justify-center md:justify-end">
          <DashboardMockup />
        </div>
      </div>
    </section>
  )
}
