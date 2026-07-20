import type { ReactNode } from 'react'
import { Route, Routes } from 'react-router-dom'
import { AccessGate } from './components/AccessGate'
import { TopNav } from './components/layout/TopNav'
import { UploadPage } from './pages/UploadPage'
import { PortfolioPage } from './pages/PortfolioPage'
import { ClientDetailPage } from './pages/ClientDetailPage'
import { ChatPage } from './pages/ChatPage'

function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
      <TopNav />
      {children}
    </div>
  )
}

function App() {
  return (
    <AccessGate>
      <Routes>
        <Route path="/" element={<UploadPage />} />
        <Route
          path="/portfolio/:workspaceId"
          element={
            <AppShell>
              <PortfolioPage />
            </AppShell>
          }
        />
        <Route
          path="/portfolio/:workspaceId/clients/:clientId"
          element={
            <AppShell>
              <ClientDetailPage />
            </AppShell>
          }
        />
        <Route
          path="/portfolio/:workspaceId/chat"
          element={
            <AppShell>
              <ChatPage />
            </AppShell>
          }
        />
      </Routes>
    </AccessGate>
  )
}

export default App
