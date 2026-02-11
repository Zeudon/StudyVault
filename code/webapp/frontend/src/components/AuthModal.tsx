import { useState } from 'react'
import axios from 'axios'
import './AuthModal.css'

interface AuthModalProps {
  mode: 'signin' | 'signup'
  onClose: () => void
  onLogin: (userData: any, token: string) => void
  onSwitchMode: (mode: 'signin' | 'signup') => void
}

const AuthModal: React.FC<AuthModalProps> = ({ mode, onClose, onLogin, onSwitchMode }) => {
  const [formData, setFormData] = useState({
    firstName: '',
    lastName: '',
    email: '',
    password: '',
  })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value })
    setError('')
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    try {
      if (mode === 'signin') {
        const response = await axios.post('/api/auth/login', {
          email: formData.email,
          password: formData.password,
        })
        onLogin(response.data.user, response.data.token)
        onClose()
      } else {
        const response = await axios.post('/api/auth/signup', {
          first_name: formData.firstName,
          last_name: formData.lastName,
          email: formData.email,
          password: formData.password,
        })
        onLogin(response.data.user, response.data.token)
        onClose()
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'An error occurred')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close" onClick={onClose}>
          ×
        </button>
        <h2>{mode === 'signin' ? 'Sign In' : 'Sign Up'}</h2>
        <form onSubmit={handleSubmit}>
          {mode === 'signup' && (
            <>
              <div className="form-group">
                <label>First Name</label>
                <input
                  type="text"
                  name="firstName"
                  value={formData.firstName}
                  onChange={handleChange}
                  required
                />
              </div>
              <div className="form-group">
                <label>Last Name</label>
                <input
                  type="text"
                  name="lastName"
                  value={formData.lastName}
                  onChange={handleChange}
                  required
                />
              </div>
            </>
          )}
          <div className="form-group">
            <label>Email</label>
            <input
              type="email"
              name="email"
              value={formData.email}
              onChange={handleChange}
              required
            />
          </div>
          <div className="form-group">
            <label>Password</label>
            <input
              type="password"
              name="password"
              value={formData.password}
              onChange={handleChange}
              required
            />
          </div>
          {error && <div className="error-message">{error}</div>}
          <button type="submit" className="submit-button" disabled={loading}>
            {loading ? 'Please wait...' : mode === 'signin' ? 'Sign In' : 'Sign Up'}
          </button>
        </form>
        <p className="switch-mode">
          {mode === 'signin' ? "Don't have an account? " : 'Already have an account? '}
          <span onClick={() => onSwitchMode(mode === 'signin' ? 'signup' : 'signin')}>
            {mode === 'signin' ? 'Sign Up' : 'Sign In'}
          </span>
        </p>
      </div>
    </div>
  )
}

export default AuthModal
