import './LandingPage.css'

interface LandingPageProps {
  onLogin: (userData: any, token: string) => void
  onAuthClick: (mode: 'signin' | 'signup') => void
}

const LandingPage: React.FC<LandingPageProps> = ({ onAuthClick }) => {
  return (
    <div className="landing-page">
      <div className="landing-content">
        <div className="hero-section">
          <div className="hero-badge">AI-Powered Study Assistant</div>
          <h1 className="hero-title">StudyVault</h1>
          <p className="hero-subtitle">Your Personal Tutor &amp; Library</p>
          <p className="hero-description">
            Upload PDFs and videos, query your data with an intelligent chatbot,
            and learn smarter. StudyVault helps you refresh knowledge, learn better,
            and get answers quicker.
          </p>
          <div className="cta-buttons">
            <button className="btn btn-primary btn-lg" onClick={() => onAuthClick('signup')}>
              Get Started
            </button>
            <button className="btn btn-secondary btn-lg" onClick={() => onAuthClick('signin')}>
              Sign In
            </button>
          </div>
        </div>

        <div className="features-section">
          <div className="feature-card">
            <div className="feature-icon">📚</div>
            <h3>Upload &amp; Organize</h3>
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
    </div>
  )
}

export default LandingPage
