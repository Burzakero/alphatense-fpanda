import { ButtonLink } from '../ui/Button'
import { useInView } from '../../hooks/useInView'

export function CTASection() {
  const { ref, inView } = useInView<HTMLDivElement>()

  return (
    <section className="bg-brand-950 py-20">
      <div
        ref={ref}
        className={`mx-auto max-w-2xl px-4 text-center transition-all duration-700 ease-out ${
          inView ? 'translate-y-0 opacity-100' : 'translate-y-4 opacity-0'
        }`}
      >
        <h2 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">
          Turn your clients&apos; financial data into decisions, not spreadsheets.
        </h2>
        <div className="mt-8">
          <ButtonLink href="/signup" size="md" className="shadow-lg shadow-brand-900/40 hover:scale-[1.02]">
            Start for free
          </ButtonLink>
        </div>
      </div>
    </section>
  )
}
