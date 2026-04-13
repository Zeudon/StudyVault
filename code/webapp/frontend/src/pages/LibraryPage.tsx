import { useState, useEffect } from 'react'
import AddContentModal from '../components/AddContentModal'
import { useToast } from '../components/Toast'
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
  chunk_count?: number
  processing_status: 'pending' | 'processing' | 'completed' | 'failed'
  processing_error?: string
}

const POLL_INTERVAL_MS = 3000

const LibraryPage: React.FC<LibraryPageProps> = () => {
  const [showAddModal, setShowAddModal] = useState(false)
  const [libraryItems, setLibraryItems] = useState<LibraryItem[]>([])
  const [loading, setLoading] = useState(true)
  const [processingIds, setProcessingIds] = useState<Set<number>>(new Set())
  const { addToast } = useToast()

  useEffect(() => {
    fetchLibraryItems()
  }, [])

  const fetchLibraryItems = async () => {
    try {
      const token = localStorage.getItem('token')
      const response = await axios.get('/api/library', {
        headers: { Authorization: `Bearer ${token}` },
      })
      const items: LibraryItem[] = response.data
      setLibraryItems(items)
      setProcessingIds(new Set(
        items
          .filter((i) => i.processing_status === 'pending' || i.processing_status === 'processing')
          .map((i) => i.id)
      ))
    } catch (error) {
      console.error('Error fetching library items:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (processingIds.size === 0) return

    const timer = setInterval(async () => {
      try {
        const token = localStorage.getItem('token')
        const ids = Array.from(processingIds).join(',')
        const response = await axios.get(`/api/library/processing-status?ids=${ids}`, {
          headers: { Authorization: `Bearer ${token}` },
        })

        type StatusUpdate = {
          id: number
          processing_status: string
          processing_error?: string
          chunk_count?: number
        }
        const updates: StatusUpdate[] = response.data
        const nowSettled = new Set<number>()
        const pendingToasts: Array<{ type: 'success' | 'error'; message: string }> = []

        setLibraryItems((prev) =>
          prev.map((item) => {
            const update = updates.find((u) => u.id === item.id)
            if (!update) return item
            if (
              update.processing_status === 'completed' ||
              update.processing_status === 'failed'
            ) {
              nowSettled.add(item.id)
              if (!pendingToasts.some((t) => t.message.startsWith(`"${item.title}"`))) {
                if (update.processing_status === 'completed') {
                  pendingToasts.push({
                    type: 'success',
                    message: `"${item.title}" is ready — ${update.chunk_count} chunks indexed`,
                  })
                } else {
                  pendingToasts.push({
                    type: 'error',
                    message: `"${item.title}" failed: ${update.processing_error ?? 'Unknown error'}`,
                  })
                }
              }
            }
            return { ...item, ...update } as LibraryItem
          })
        )

        pendingToasts.forEach((t) => addToast(t))

        if (nowSettled.size > 0) {
          setProcessingIds((prev) => {
            const next = new Set(prev)
            nowSettled.forEach((id) => next.delete(id))
            return next
          })
        }
      } catch (error) {
        console.error('Error polling processing status:', error)
      }
    }, POLL_INTERVAL_MS)

    return () => clearInterval(timer)
  }, [processingIds])

  const handleDelete = async (id: number) => {
    if (!window.confirm('Are you sure you want to delete this item?')) return

    try {
      const token = localStorage.getItem('token')
      await axios.delete(`/api/library/${id}`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      setLibraryItems(libraryItems.filter((item) => item.id !== id))
      setProcessingIds((prev) => {
        const next = new Set(prev)
        next.delete(id)
        return next
      })
    } catch (error) {
      console.error('Error deleting item:', error)
      alert('Failed to delete item')
    }
  }

  const handleAddContent = (newItem: LibraryItem) => {
    setShowAddModal(false)
    setLibraryItems((prev) => [newItem, ...prev])
    setProcessingIds((prev) => new Set([...prev, newItem.id]))
  }

  const handleViewPDF = async (id: number) => {
    try {
      const token = localStorage.getItem('token')
      const response = await axios.get(`/api/library/${id}/download`, {
        headers: { Authorization: `Bearer ${token}` },
        responseType: 'blob',
      })
      const blob = new Blob([response.data], { type: 'application/pdf' })
      const url = window.URL.createObjectURL(blob)
      window.open(url, '_blank')
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
      <div className="library-content">
        <div className="library-header">
          <h1>My Library</h1>
          <button className="btn btn-primary" onClick={() => setShowAddModal(true)}>
            + Add Content
          </button>
        </div>

        {loading ? (
          <div className="library-state">Loading your library...</div>
        ) : libraryItems.length === 0 ? (
          <div className="library-state">
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
                  {item.processing_status === 'pending' && (
                    <p className="item-status status-pending">Queued for processing...</p>
                  )}
                  {item.processing_status === 'processing' && (
                    <p className="item-status status-processing">
                      <span className="spinner" /> Processing...
                    </p>
                  )}
                  {item.processing_status === 'completed' && item.chunk_count != null && (
                    <p className="item-status status-completed">{item.chunk_count} chunks indexed</p>
                  )}
                  {item.processing_status === 'failed' && (
                    <p className="item-status status-failed">
                      Processing failed{item.processing_error ? `: ${item.processing_error}` : ''}
                    </p>
                  )}
                  <div className="item-actions">
                    {item.type === 'pdf' ? (
                      <button
                        className="btn btn-secondary btn-sm"
                        onClick={() => handleViewPDF(item.id)}
                      >
                        Download PDF
                      </button>
                    ) : (
                      <button
                        className="btn btn-secondary btn-sm"
                        onClick={() => handleViewYouTube(item.url)}
                      >
                        Watch Video
                      </button>
                    )}
                  </div>
                </div>
                <button
                  className="btn btn-danger btn-icon delete-btn"
                  onClick={() => handleDelete(item.id)}
                  aria-label="Delete item"
                >
                  ✕
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
