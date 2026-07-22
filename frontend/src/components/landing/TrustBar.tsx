import { useInView } from '../../hooks/useInView'

// Alphatense has no public customer logos yet (still in pilot validation) — placeholder
// marks stand in for real logos rather than fabricating false social proof.
const PLACEHOLDER_MARKS = ['Advisory Co.', 'Ledger Partners', 'Northfield FP&A', 'Harrow & Vale', 'Clearwater Group']

export function TrustBar() {
  const { ref, inView } = useInView<HTMLDivElement>()

  return (
    <section className="border-b border-slate-200 bg-white py-12 dark:border-slate-800 dark:bg-slate-950">
      <div
        ref={ref}
        className={`mx-auto max-w-5xl px-4 text-center transition-all duration-700 ease-out ${
          inView ? 'translate-y-0 opacity-100' : 'translate-y-4 opacity-0'
        }`}
      >
        <p className="text-xs font-medium tracking-wide text-slate-400 uppercase dark:text-slate-500">
          Built for financial advisory firms across the UK and US
        </p>
        <div className="mt-6 flex flex-wrap items-center justify-center gap-x-10 gap-y-4">
          {PLACEHOLDER_MARKS.map((mark) => (
            <span
              key={mark}
              className="text-lg font-semibold text-slate-300 transition hover:text-brand-500 dark:text-slate-700 dark:hover:text-brand-400"
            >
              {mark}
            </span>
          ))}
        </div>
      </div>
    </section>
  )
}
