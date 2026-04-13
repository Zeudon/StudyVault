import { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import axios from 'axios'
import LandingPage from './pages/LandingPage'
import LibraryPage from './pages/LibraryPage'
import Navbar from './components/Navbar'
import ChatPanel from './components/ChatPanel'
import AuthModal from './components/AuthModal'
import { ToastProvider } from './components/Toast'
import './App.css'

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false)
  const [user, setUser] = useState<any>(null)
  const [isChatPanelOpen, setIsChatPanelOpen] = useState(false)
  const [showAuthModal, setShowAuthModal] = useState(false)
  const [authMode, setAuthMode] = useState<'signin' | 'signup'>('signin')

  useEffect(() => {
    const token = localStorage.getItem('token')
    const userData = localStorage.getItem('user')
    if (token && userData) {
      setIsAuthenticated(true)
      setUser(JSON.parse(userData))
    }
  }, [])

  const handleLogin = (userData: any, token: string) => {
    localStorage.setItem('token', token)
    localStorage.setItem('user', JSON.stringify(userData))
    setUser(userData)
    setIsAuthenticated(true)
    setShowAuthModal(false)
  }

  const handleLogout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    setUser(null)
    setIsAuthenticated(false)
    setIsChatPanelOpen(false)
  }

  // Auto-logout when the API returns 401 (expired token)
  useEffect(() => {
    const id = axios.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401 && isAuthenticated) {
          handleLogout()
        }
        return Promise.reject(error)
      }
    )
    return () => axios.interceptors.response.eject(id)
  }, [isAuthenticated])

  const handleAuthClick = (mode: 'signin' | 'signup') => {
    setAuthMode(mode)
    setShowAuthModal(true)
  }

  return (
    <ToastProvider>
      <Router>
        <div className="app-shell">
          <Navbar
            isAuthenticated={isAuthenticated}
            onAuthClick={handleAuthClick}
            onLogout={handleLogout}
            onChatToggle={() => setIsChatPanelOpen(p => !p)}
            isChatPanelOpen={isChatPanelOpen}
          />

          <div className={`app-main${isChatPanelOpen ? ' app-main--panel-open' : ''}`}>
            <Routes>
              <Route
                path="/"
                element={
                  isAuthenticated ? (
                    <Navigate to="/library" replace />
                  ) : (
                    <LandingPage onLogin={handleLogin} onAuthClick={handleAuthClick} />
                  )
                }
              />
              <Route
                path="/library"
                element={
                  isAuthenticated ? (
                    <LibraryPage user={user} onLogout={handleLogout} />
                  ) : (
                    <Navigate to="/" replace />
                  )
                }
              />
              {/* Legacy /chat route — redirects to library (panel opened via Navbar) */}
              <Route path="/chat" element={<Navigate to="/library" replace />} />
            </Routes>
          </div>

          <ChatPanel
            isOpen={isChatPanelOpen}
            user={user}
            onClose={() => setIsChatPanelOpen(false)}
          />

          {showAuthModal && (
            <AuthModal
              mode={authMode}
              onClose={() => setShowAuthModal(false)}
              onLogin={handleLogin}
              onSwitchMode={setAuthMode}
            />
          )}
        </div>
      </Router>
    </ToastProvider>
  )
}

export default App
