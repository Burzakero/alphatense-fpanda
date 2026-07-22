import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ButtonLink } from '../ui/Button'

const NAV_LINKS = [
  { href: '#capabilities', label: 'Product' },
  { href: '#how-it-works', label: 'How it works' },
  { href: '#use-cases', label: 'Use cases' },
]

export function Header() {
  const [scrolled, setScrolled] = useState(false)

  useEffect(() => {
    function handleScroll() {
      setScrolled(window.scrollY > 8)
    }
    handleScroll()
    window.addEventListener('scroll', handleScroll, { passive: true })
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  return (
    <header
      className={`fixed inset-x-0 top-0 z-50 transition-colors duration-300 ${
        scrolled ? 'border-b border-white/10 bg-brand-950/95 backdrop-blur' : 'border-b border-transparent bg-transparent'
      }`}
    >
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4">
        <Link to="/" className="flex items-center gap-2">
          <img src="/logo-mark-192.png" alt="" className="h-8 w-8" />
          <span translate="no" className="notranslate text-lg font-semibold text-white">
            Alphatense
          </span>
        </Link>

        <nav className="hidden items-center gap-8 md:flex">
          {NAV_LINKS.map(({ href, label }) => (
            <a key={href} href={href} className="text-sm font-medium text-slate-300 transition hover:text-white">
              {label}
            </a>
          ))}
        </nav>

        <div className="flex items-center gap-4">
          <Link to="/login" className="text-sm font-medium text-slate-300 transition hover:text-white">
            Log in
          </Link>
          <ButtonLink href="/signup" size="sm" className="shadow-md shadow-brand-900/30 hover:scale-[1.02]">
            Start for free
          </ButtonLink>
        </div>
      </div>
    </header>
  )
}
