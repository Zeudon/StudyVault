import { useState, useEffect } from 'react'
import Navbar from '../components/Navbar'
import AddContentModal from '../components/AddContentModal'
import axios from 'axios'
import './LibraryPage.css'

interface LibraryPageProps {
  user: any
  onLogout: () => void
}

interface LibraryItem {
  id: number
  title: string
  type: 'pdf' | 'youtube'
  url: string
  created_at: string
}

const LibraryPage: React.FC<LibraryPageProps> = ({ onLogout }) => {
  const [showAddModal, setShowAddModal] = useState(false)
  const [libraryItems, setLibraryItems] = useState<LibraryItem[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchLibraryItems()
  }, [])

  const fetchLibraryItems = async () => {
    try {
      const token = localStorage.getItem('token')
      const response = await axios.get('/api/library', {
        headers: { Authorization: `Bearer ${token}` },
      })
      setLibraryItems(response.data)
    } catch (error) {
      console.error('Error fetching library items:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (id: number) => {
    if (!window.confirm('Are you sure you want to delete this item?')) {
      return
    }

    try {
      const token = localStorage.getItem('token')
      await axios.delete(`/api/library/${id}`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      setLibraryItems(libraryItems.filter((item) => item.id !== id))
    } catch (error) {
      console.error('Error deleting item:', error)
      alert('Failed to delete item')
    }
  }

  const handleAddContent = () => {
    setShowAddModal(false)
    fetchLibraryItems()
  }

  const handleViewPDF = async (id: number) => {
    try {
      const token = localStorage.getItem('token')
      const response = await axios.get(`/api/library/${id}/download`, {
        headers: { Authorization: `Bearer ${token}` },
        responseType: 'blob',
      })
      
      // Create a blob URL and open in new tab
      const blob = new Blob([response.data], { type: 'application/pdf' })
      const url = window.URL.createObjectURL(blob)
      window.open(url, '_blank')
      
      // Clean up the URL after a short delay
      setTimeout(() => window.URL.revokeObjectURL(url), 100)
    } catch (error) {
      console.error('Error viewing PDF:', error)
      alert('Failed to open PDF')
    }
  }

  const handleViewYouTube = (url: string) => {
    window.open(url, '_blank')
  }

  return (
    <div className="library-page">
      <Navbar
        isAuthenticated={true}
        onAuthClick={() => {}}
        onLogout={onLogout}
      />
      <div className="library-content">
        <div className="library-header">
          <h1>My Library</h1>
          <button className="add-button" onClick={() => setShowAddModal(true)}>
            + Add Content
          </button>
        </div>

        {loading ? (
          <div className="loading">Loading your library...</div>
        ) : libraryItems.length === 0 ? (
          <div className="empty-state">
            <p>Your library is empty. Start by adding some content!</p>
          </div>
        ) : (
          <div className="library-grid">
            {libraryItems.map((item) => (
              <div key={item.id} className="library-item">
                <div className="item-icon">
                  {item.type === 'pdf' ? '📄' : '🎥'}
                </div>
                <div className="item-content">
                  <h3>{item.title}</h3>
                  <p className="item-type">
                    {item.type === 'pdf' ? 'PDF Document' : 'YouTube Video'}
                  </p>
                  <p className="item-date">
                    Added: {new Date(item.created_at).toLocaleDateString()}
                  </p>
                  <div className="item-actions">
                    {item.type === 'pdf' ? (
                      <button
                        className="view-button"
                        onClick={() => handleViewPDF(item.id)}
                      >
                        📥 Download PDF
                      </button>
                    ) : (
                      <button
                        className="view-button"
                        onClick={() => handleViewYouTube(item.url)}
                      >
                        ▶️ Watch Video
                      </button>
                    )}
                  </div>
                </div>
                <button
                  className="delete-button"
                  onClick={() => handleDelete(item.id)}
                >
                  🗑️
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {showAddModal && (
        <AddContentModal
          onClose={() => setShowAddModal(false)}
          onSuccess={handleAddContent}
        />
      )}
    </div>
  )
}

export default LibraryPage
