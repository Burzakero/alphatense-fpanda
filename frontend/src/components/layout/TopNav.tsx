import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { LogOut } from 'lucide-react'
import { logout } from '../../api/client'
import { useAuth } from '../../auth/context'

export function TopNav() {
  const { advisor } = useAuth()
  const navigate = useNavigate()
  const [loggingOut, setLoggingOut] = useState(false)

  async function handleLogout() {
    setLoggingOut(true)
    try {
      await logout()
    } finally {
      navigate('/login')
    }
  }

  return (
    <header className="sticky top-0 z-40 border-b border-white/10 bg-brand-950">
      <div className="mx-auto flex max-w-5xl items-center justify-between gap-2 px-4 py-3">
        <Link to="/home" className="flex items-center gap-2">
          <img src="/logo-mark-192.png" alt="" className="h-8 w-8" />
          <span translate="no" className="notranslate text-lg font-semibold tracking-tight text-white">
            Alphatense
          </span>
        </Link>
        <div className="flex items-center gap-3">
          <span className="hidden text-sm text-slate-300 sm:inline">{advisor.name}</span>
          <button
            type="button"
            onClick={handleLogout}
            disabled={loggingOut}
            className="inline-flex items-center gap-1.5 rounded-md px-2 py-1.5 text-sm text-slate-300 transition hover:bg-white/10 hover:text-white disabled:opacity-40"
          >
            <LogOut className="h-4 w-4" />
            Log out
          </button>
        </div>
      </div>
    </header>
  )
}
