import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { Navigate } from 'react-router-dom'
import { type Advisor, getMe, getToken } from '../api/client'
import { AuthContext } from '../auth/context'

type Status = 'checking' | 'authenticated' | 'anonymous'

export function RequireAuth({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<Status>('checking')
  const [advisor, setAdvisor] = useState<Advisor | null>(null)
  const [workspaceIds, setWorkspaceIds] = useState<string[]>([])

  async function refresh() {
    const me = await getMe()
    setAdvisor(me.advisor)
    setWorkspaceIds(me.workspace_ids)
    setStatus('authenticated')
  }

  useEffect(() => {
    if (!getToken()) {
      setStatus('anonymous')
      return
    }
    refresh().catch(() => setStatus('anonymous'))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  if (status === 'checking') return null
  if (status === 'anonymous' || !advisor) return <Navigate to="/login" replace />

  return <AuthContext.Provider value={{ advisor, workspaceIds, refresh }}>{children}</AuthContext.Provider>
}
