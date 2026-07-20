import type { ButtonHTMLAttributes, AnchorHTMLAttributes, ReactNode } from 'react'

const BASE =
  'inline-flex items-center justify-center gap-2 rounded-md bg-brand-600 text-sm font-medium text-white transition hover:bg-brand-700 disabled:opacity-40 disabled:hover:bg-brand-600'

const SIZE = {
  sm: 'px-3 py-1.5',
  md: 'px-4 py-2',
}

export function Button({
  size = 'md',
  className = '',
  children,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { size?: keyof typeof SIZE; children: ReactNode }) {
  return (
    <button className={`${BASE} ${SIZE[size]} ${className}`} {...props}>
      {children}
    </button>
  )
}

export function ButtonLink({
  size = 'md',
  className = '',
  children,
  ...props
}: AnchorHTMLAttributes<HTMLAnchorElement> & { size?: keyof typeof SIZE; children: ReactNode }) {
  return (
    <a className={`${BASE} ${SIZE[size]} ${className}`} {...props}>
      {children}
    </a>
  )
}
