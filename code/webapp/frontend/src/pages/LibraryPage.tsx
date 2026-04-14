import { useState, useEffect } from 'react'
import AddContentModal from '../components/AddContentModal'
import ConfirmModal from '../components/ConfirmModal'
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
  const [searchQuery, setSearchQuery] = useState('')
  const [typeFilter, setTypeFilter] = useState<'all' | 'pdf' | 'youtube'>('all')
  const [deleteTarget, setDeleteTarget] = useState<{ id: number; title: string } | null>(null)
  const [sortOrder, setSortOrder] = useState<'newest' | 'oldest' | 'az'>('newest')
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
      addToast({ type: 'error', message: 'Failed to delete item' })
    } finally {
      setDeleteTarget(null)
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
      addToast({ type: 'error', message: 'Failed to open PDF' })
    }
  }

  const handleViewYouTube = (url: string) => {
    window.open(url, '_blank')
  }

  // Derived filtered + sorted list
  const filteredItems = libraryItems
    .filter((item) => {
      const matchesType = typeFilter === 'all' || item.type === typeFilter
      const matchesSearch = item.title.toLowerCase().includes(searchQuery.toLowerCase())
      return matchesType && matchesSearch
    })
    .sort((a, b) => {
      if (sortOrder === 'oldest') return new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
      if (sortOrder === 'az') return a.title.localeCompare(b.title)
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime() // newest
    })

  return (
    <div className="library-page">
      <div className="library-content">
        <div className="library-header">
          <h1>
            My Library
            {!loading && libraryItems.length > 0 && (
              <span className="library-count">
                · {filteredItems.length} {filteredItems.length === 1 ? 'Item' : 'Items'}
              </span>
            )}
          </h1>
          <button className="btn btn-primary" onClick={() => setShowAddModal(true)}>
            + Add Content
          </button>
        </div>

        {/* Search + filter controls */}
        {!loading && libraryItems.length > 0 && (
          <div className="library-controls">
            <input
              type="search"
              className="library-search"
              placeholder="Search your library…"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            <div className="library-filters">
              <button
                className={`btn btn-sm ${typeFilter === 'all' ? 'btn-primary' : 'btn-ghost'}`}
                onClick={() => setTypeFilter('all')}
              >
                All
              </button>
              <button
                className={`btn btn-sm ${typeFilter === 'pdf' ? 'btn-primary' : 'btn-ghost'}`}
                onClick={() => setTypeFilter('pdf')}
              >
                PDFs
              </button>
              <button
                className={`btn btn-sm ${typeFilter === 'youtube' ? 'btn-primary' : 'btn-ghost'}`}
                onClick={() => setTypeFilter('youtube')}
              >
                Videos
              </button>
            </div>
            <select
              className="library-sort"
              value={sortOrder}
              onChange={(e) => setSortOrder(e.target.value as 'newest' | 'oldest' | 'az')}
              aria-label="Sort by"
            >
              <option value="newest">Newest</option>
              <option value="oldest">Oldest</option>
              <option value="az">A → Z</option>
            </select>
          </div>
        )}

        {loading ? (
          // Skeleton loading cards
          <div className="library-grid">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="library-item skeleton-card">
                <div className="skeleton skeleton-icon" />
                <div className="skeleton-content">
                  <div className="skeleton skeleton-title" />
                  <div className="skeleton skeleton-line" />
                  <div className="skeleton skeleton-line skeleton-line--short" />
                </div>
              </div>
            ))}
          </div>
        ) : libraryItems.length === 0 ? (
          <div className="library-empty">
            <div className="library-empty-icon">📚</div>
            <h2 className="library-empty-title">Your library is empty</h2>
            <p className="library-empty-desc">Upload PDFs or add YouTube videos to start building your knowledge base.</p>
            <button className="btn btn-primary" onClick={() => setShowAddModal(true)}>
              + Add Content
            </button>
          </div>
        ) : filteredItems.length === 0 ? (
          <div className="library-state">
            <p>No items match your search.</p>
          </div>
        ) : (
          <div className="library-grid">
            {filteredItems.map((item) => (
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
                  onClick={() => setDeleteTarget({ id: item.id, title: item.title })}
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

      {deleteTarget && (
        <ConfirmModal
          title="Delete item?"
          message={`"${deleteTarget.title}" will be permanently removed from your library and cannot be recovered.`}
          confirmLabel="Delete"
          onConfirm={() => handleDelete(deleteTarget.id)}
          onCancel={() => setDeleteTarget(null)}
        />
      )}
    </div>
  )
}

export default LibraryPage
