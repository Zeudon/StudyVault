import { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import LandingPage from './pages/LandingPage'
import LibraryPage from './pages/LibraryPage'
import './App.css'

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false)
  const [user, setUser] = useState<any>(null)

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
  }

  const handleLogout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    setUser(null)
    setIsAuthenticated(false)
  }

  return (
    <Router>
      <Routes>
        <Route
          path="/"
          element={
            isAuthenticated ? (
              <Navigate to="/library" replace />
            ) : (
              <LandingPage onLogin={handleLogin} />
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
      </Routes>
    </Router>
  )
}

export default App
