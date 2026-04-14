import { useState, useRef } from 'react'
import axios from 'axios'
import './AddContentModal.css'

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

interface AddContentModalProps {
  onClose: () => void
  onSuccess: (newItem: LibraryItem) => void
}

const AddContentModal: React.FC<AddContentModalProps> = ({ onClose, onSuccess }) => {
  const [contentType, setContentType] = useState<'pdf' | 'youtube'>('pdf')
  const [title, setTitle] = useState('')
  const [url, setUrl] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [isDragging, setIsDragging] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const applyFile = (f: File) => {
    setFile(f)
    if (!title) setTitle(f.name)
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) applyFile(e.target.files[0])
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    const dropped = e.dataTransfer.files[0]
    if (dropped && dropped.type === 'application/pdf') {
      applyFile(dropped)
    } else if (dropped) {
      setError('Only PDF files are supported')
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    try {
      const token = localStorage.getItem('token')
      const formData = new FormData()
      formData.append('title', title)
      formData.append('type', contentType)

      if (contentType === 'pdf') {
        if (!file) {
          setError('Please select a PDF file')
          setLoading(false)
          return
        }
        formData.append('file', file)
      } else {
        formData.append('url', url)
      }

      const response = await axios.post('/api/library/upload', formData, {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'multipart/form-data',
        },
      })

      onSuccess(response.data)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to add content')
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
        <h2>Add Content</h2>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Content Type</label>
            <div className="type-selector">
              <button
                type="button"
                className={`type-button ${contentType === 'pdf' ? 'active' : ''}`}
                onClick={() => setContentType('pdf')}
              >
                📄 PDF
              </button>
              <button
                type="button"
                className={`type-button ${contentType === 'youtube' ? 'active' : ''}`}
                onClick={() => setContentType('youtube')}
              >
                🎥 YouTube
              </button>
            </div>
          </div>

          <div className="form-group">
            <label>Title</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
            />
          </div>

          {contentType === 'pdf' ? (
            <div className="form-group">
              <label>Upload PDF</label>
              <div
                className={`drop-zone${isDragging ? ' drop-zone--active' : ''}${file ? ' drop-zone--has-file' : ''}`}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
              >
                {file ? (
                  <span className="drop-zone-filename">📄 {file.name}</span>
                ) : (
                  <>
                    <span className="drop-zone-icon">⬆</span>
                    <span className="drop-zone-label">Drag &amp; drop a PDF here, or <u>browse</u></span>
                  </>
                )}
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf"
                  onChange={handleFileChange}
                  required={!file}
                  style={{ display: 'none' }}
                />
              </div>
            </div>
          ) : (
            <div className="form-group">
              <label>YouTube URL</label>
              <input
                type="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://www.youtube.com/watch?v=..."
                required
              />
            </div>
          )}

          {error && <div className="error-message">{error}</div>}

          <button type="submit" className="submit-button" disabled={loading}>
            {loading ? 'Adding...' : 'Add Content'}
          </button>
        </form>
      </div>
    </div>
  )
}

export default AddContentModal
