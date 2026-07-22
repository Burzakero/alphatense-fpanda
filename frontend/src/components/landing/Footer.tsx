import { CONTACT_EMAIL } from '../../constants'

const PRODUCT_LINKS = [
  { href: '#capabilities', label: 'Product' },
  { href: '#how-it-works', label: 'How it works' },
  { href: '#use-cases', label: 'Use cases' },
]

export function Footer() {
  return (
    <footer className="bg-slate-950 py-14">
      <div className="mx-auto grid max-w-6xl grid-cols-1 gap-10 px-4 sm:grid-cols-[2fr_1fr]">
        <div className="flex items-center gap-2">
          <img src="/logo-mark-192.png" alt="" className="h-7 w-7" />
          <span translate="no" className="notranslate text-base font-semibold text-white">
            Alphatense
          </span>
        </div>

        <div>
          <p className="text-xs font-semibold tracking-wide text-slate-500 uppercase">Product</p>
          <ul className="mt-3 space-y-2">
            {PRODUCT_LINKS.map(({ href, label }) => (
              <li key={href}>
                <a href={href} className="text-sm text-slate-400 transition hover:text-white">
                  {label}
                </a>
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div className="mx-auto mt-10 flex max-w-6xl flex-col items-center justify-between gap-3 border-t border-white/10 px-4 pt-6 text-sm text-slate-500 sm:flex-row">
        <span translate="no" className="notranslate">
          © {new Date().getFullYear()} Alphatense
        </span>
        <a href={`mailto:${CONTACT_EMAIL}`} className="transition hover:text-white">
          {CONTACT_EMAIL}
        </a>
      </div>
    </footer>
  )
}
