import { createContext, useContext } from 'react'
import type { Advisor } from '../api/client'

export interface AuthContextValue {
  advisor: Advisor
  workspaceIds: string[]
  refresh: () => Promise<void>
}

export const AuthContext = createContext<AuthContextValue | null>(null)

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be called from inside <RequireAuth>')
  return ctx
}
