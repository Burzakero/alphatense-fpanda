import { Link } from 'react-router-dom'

export function TopNav() {
  return (
    <header className="border-b border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
      <div className="mx-auto flex max-w-5xl items-center gap-2 px-4 py-3">
        <Link to="/" className="flex items-center gap-2">
          <img src="/logo-mark-192.png" alt="" className="h-8 w-8" />
          <span
            translate="no"
            className="notranslate text-lg font-semibold tracking-tight text-brand-700 dark:text-brand-300"
          >
            Alphatense
          </span>
        </Link>
      </div>
    </header>
  )
}
