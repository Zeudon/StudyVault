import './Navbar.css'

interface NavbarProps {
  isAuthenticated: boolean
  onAuthClick: (mode: 'signin' | 'signup') => void
  onLogout: () => void
}

const Navbar: React.FC<NavbarProps> = ({ isAuthenticated, onAuthClick, onLogout }) => {
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
              <button className="nav-button">Library</button>
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
