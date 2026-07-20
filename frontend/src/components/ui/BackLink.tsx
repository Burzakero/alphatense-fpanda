import { ArrowLeft } from 'lucide-react'
import { Link } from 'react-router-dom'

export function BackLink({ to, children }: { to: string; children: React.ReactNode }) {
  return (
    <Link
      to={to}
      className="inline-flex items-center gap-1.5 text-sm text-brand-600 hover:text-brand-700 hover:underline dark:text-brand-400 dark:hover:text-brand-300"
    >
      <ArrowLeft className="h-4 w-4" />
      {children}
    </Link>
  )
}
