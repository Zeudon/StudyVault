import { useState } from 'react'
import Navbar from '../components/Navbar'
import AuthModal from '../components/AuthModal'
import './LandingPage.css'

interface LandingPageProps {
  onLogin: (userData: any, token: string) => void
}

const LandingPage: React.FC<LandingPageProps> = ({ onLogin }) => {
  const [showAuthModal, setShowAuthModal] = useState(false)
  const [authMode, setAuthMode] = useState<'signin' | 'signup'>('signin')

  const handleAuthClick = (mode: 'signin' | 'signup') => {
    setAuthMode(mode)
    setShowAuthModal(true)
  }

  return (
    <div className="landing-page">
      <Navbar
        isAuthenticated={false}
        onAuthClick={handleAuthClick}
        onLogout={() => {}}
      />
      <div className="landing-content">
        <div className="hero-section">
          <h1 className="hero-title">StudyVault</h1>
          <p className="hero-subtitle">
            Your Personal Tutor & Library
          </p>
          <p className="hero-description">
            Upload PDFs and videos, query your data with an intelligent chatbot,
            and learn smarter. StudyVault helps you refresh knowledge, learn better,
            and get answers quicker.
          </p>
          <div className="cta-buttons">
            <button
              className="cta-button primary"
              onClick={() => handleAuthClick('signup')}
            >
              Get Started
            </button>
            <button
              className="cta-button secondary"
              onClick={() => handleAuthClick('signin')}
            >
              Sign In
            </button>
          </div>
        </div>
        <div className="features-section">
          <div className="feature-card">
            <div className="feature-icon">📚</div>
            <h3>Upload & Organize</h3>
            <p>Store your PDFs and YouTube videos in one place</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">💬</div>
            <h3>AI-Powered Chat</h3>
            <p>Query your content and get instant answers</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">🎯</div>
            <h3>Learn Smarter</h3>
            <p>Refresh knowledge and master concepts faster</p>
          </div>
        </div>
      </div>
      {showAuthModal && (
        <AuthModal
          mode={authMode}
          onClose={() => setShowAuthModal(false)}
          onLogin={onLogin}
          onSwitchMode={(mode) => setAuthMode(mode)}
        />
      )}
    </div>
  )
}

export default LandingPage
