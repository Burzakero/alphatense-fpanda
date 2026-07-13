import { Route, Routes } from 'react-router-dom'
import { AccessGate } from './components/AccessGate'
import { UploadPage } from './pages/UploadPage'
import { PortfolioPage } from './pages/PortfolioPage'
import { ClientDetailPage } from './pages/ClientDetailPage'
import { ChatPage } from './pages/ChatPage'

function App() {
  return (
    <AccessGate>
      <Routes>
        <Route path="/" element={<UploadPage />} />
        <Route path="/portfolio/:workspaceId" element={<PortfolioPage />} />
        <Route path="/portfolio/:workspaceId/clients/:clientId" element={<ClientDetailPage />} />
        <Route path="/portfolio/:workspaceId/chat" element={<ChatPage />} />
      </Routes>
    </AccessGate>
  )
}

export default App
