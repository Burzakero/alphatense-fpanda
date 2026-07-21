import type { ReactNode } from 'react'
import { Route, Routes } from 'react-router-dom'
import { RequireAuth } from './components/RequireAuth'
import { TopNav } from './components/layout/TopNav'
import { LandingPage } from './pages/LandingPage'
import { LoginPage } from './pages/LoginPage'
import { SignupPage } from './pages/SignupPage'
import { HomePage } from './pages/HomePage'
import { UploadPage } from './pages/UploadPage'
import { PortfolioPage } from './pages/PortfolioPage'
import { ClientDetailPage } from './pages/ClientDetailPage'
import { ChatPage } from './pages/ChatPage'

function AppShell({ children }: { children: ReactNode }) {
  return (
    <RequireAuth>
      <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
        <TopNav />
        {children}
      </div>
    </RequireAuth>
  )
}

function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/signup" element={<SignupPage />} />
      <Route
        path="/home"
        element={
          <AppShell>
            <HomePage />
          </AppShell>
        }
      />
      <Route
        path="/upload"
        element={
          <AppShell>
            <UploadPage />
          </AppShell>
        }
      />
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
  )
}

export default App
