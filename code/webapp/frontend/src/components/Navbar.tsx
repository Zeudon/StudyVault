import { useNavigate, useLocation } from 'react-router-dom'
import './Navbar.css'

interface NavbarProps {
  isAuthenticated: boolean
  onAuthClick: (mode: 'signin' | 'signup') => void
  onLogout: () => void
  onChatToggle: () => void
  isChatPanelOpen: boolean
}

const Navbar: React.FC<NavbarProps> = ({
  isAuthenticated,
  onAuthClick,
  onLogout,
  onChatToggle,
  isChatPanelOpen,
}) => {
  const navigate = useNavigate()
  const location = useLocation()

  return (
    <nav className={`navbar${isChatPanelOpen ? ' navbar--panel-open' : ''}`}>
      <div className="navbar-content">
        <button className="navbar-logo" onClick={() => navigate(isAuthenticated ? '/library' : '/')}>
          <div className="logo-mark">SV</div>
          <span className="logo-text">StudyVault</span>
        </button>

        <div className="navbar-actions">
          {isAuthenticated ? (
            <>
              <button
                className={`btn btn-ghost btn-sm${location.pathname === '/library' ? ' active' : ''}`}
                onClick={() => navigate('/library')}
              >
                Library
              </button>
              <button
                className={`btn btn-ghost btn-sm nav-chat-btn${isChatPanelOpen ? ' active' : ''}`}
                onClick={onChatToggle}
              >
                Chat
              </button>
              <button className="btn btn-danger btn-sm" onClick={onLogout}>
                Log Out
              </button>
            </>
          ) : (
            <>
              <button className="btn btn-ghost btn-sm" onClick={() => onAuthClick('signin')}>
                Sign In
              </button>
              <button className="btn btn-primary btn-sm" onClick={() => onAuthClick('signup')}>
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
