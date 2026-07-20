import type { HTMLAttributes, ReactNode } from 'react'

export function Card({
  className = '',
  children,
  ...props
}: HTMLAttributes<HTMLDivElement> & { children: ReactNode }) {
  return (
    <div
      className={`rounded-lg border border-slate-200 bg-white shadow-sm dark:border-slate-700 dark:bg-slate-900 ${className}`}
      {...props}
    >
      {children}
    </div>
  )
}
