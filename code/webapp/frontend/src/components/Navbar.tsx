import { useNavigate, useLocation } from 'react-router-dom'
import './Navbar.css'

interface NavbarProps {
  isAuthenticated: boolean
  onAuthClick: (mode: 'signin' | 'signup') => void
  onLogout: () => void
}

const Navbar: React.FC<NavbarProps> = ({ isAuthenticated, onAuthClick, onLogout }) => {
  const navigate = useNavigate()
  const location = useLocation()

  return (
    <nav className="navbar">
      <div className="navbar-content">
        <div className="navbar-logo">
          <span className="logo-icon">📚</span>
          <span className="logo-text">StudyVault</span>
        </div>
        <div className="navbar-actions">
          {isAuthenticated ? (
            <>
              <button
                className={`nav-button${location.pathname === '/library' ? ' active' : ''}`}
                onClick={() => navigate('/library')}
              >
                Library
              </button>
              <button
                className={`nav-button${location.pathname === '/chat' ? ' active' : ''}`}
                onClick={() => navigate('/chat')}
              >
                Chat
              </button>
              <button className="nav-button logout" onClick={onLogout}>
                Log Out
              </button>
            </>
          ) : (
            <>
              <button className="nav-button" onClick={() => onAuthClick('signin')}>
                Sign In
              </button>
              <button className="nav-button signup" onClick={() => onAuthClick('signup')}>
                Sign Up
              </button>
            </>
          )}
        </div>
      </div>
    </nav>
  )
}

export default Navbar
