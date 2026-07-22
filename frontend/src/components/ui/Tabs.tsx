import { Link } from 'react-router-dom'

export interface TabItem {
  key: string
  label: string
  to: string
}

export function Tabs({ items, active }: { items: TabItem[]; active: string }) {
  return (
    <div className="border-b border-slate-200 dark:border-slate-800">
      <nav className="-mb-px flex gap-6">
        {items.map((item) => {
          const isActive = item.key === active
          return (
            <Link
              key={item.key}
              to={item.to}
              className={`border-b-2 px-1 py-3 text-sm font-medium transition ${
                isActive
                  ? 'border-brand-600 text-brand-600 dark:border-brand-400 dark:text-brand-400'
                  : 'border-transparent text-slate-500 hover:border-slate-300 hover:text-slate-700 dark:text-slate-400 dark:hover:border-slate-600 dark:hover:text-slate-200'
              }`}
            >
              {item.label}
            </Link>
          )
        })}
      </nav>
    </div>
  )
}
