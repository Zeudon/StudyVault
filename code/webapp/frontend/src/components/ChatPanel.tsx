import { useState, useRef, useEffect } from 'react'
import './ChatPanel.css'

interface Source {
  title: string
  type: string
  url: string
  relevance_score: number
}

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources?: Source[]
  loading?: boolean
}

interface ChatPanelProps {
  isOpen: boolean
  user: any
  onClose: () => void
}

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const ChatPanel: React.FC<ChatPanelProps> = ({ isOpen, user, onClose }) => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content: `Hi ${user?.first_name ?? 'there'}! Ask me anything about your uploaded documents and videos.`,
    },
  ])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Focus input when panel opens
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 300)
    }
  }, [isOpen])

  const sendMessage = async () => {
    const query = input.trim()
    if (!query || isLoading) return

    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: query,
    }
    const placeholderMsg: Message = {
      id: Date.now().toString() + '-loading',
      role: 'assistant',
      content: '',
      loading: true,
    }

    setMessages(prev => [...prev, userMsg, placeholderMsg])
    setInput('')
    setIsLoading(true)

    try {
      const token = localStorage.getItem('token')
      const res = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ user_query: query }),
      })

      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()

      setMessages(prev =>
        prev.map(m =>
          m.id === placeholderMsg.id
            ? { ...m, content: data.response, sources: data.sources ?? [], loading: false }
            : m
        )
      )
    } catch {
      setMessages(prev =>
        prev.map(m =>
          m.id === placeholderMsg.id
            ? { ...m, content: 'Sorry, something went wrong. Please try again.', loading: false }
            : m
        )
      )
    } finally {
      setIsLoading(false)
      inputRef.current?.focus()
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <div className={`chat-panel${isOpen ? ' chat-panel--open' : ''}`} aria-hidden={!isOpen}>
      {/* Panel header */}
      <div className="chat-panel-header">
        <div className="chat-panel-title">
          <span className="chat-panel-title-text">AI Assistant</span>
          <span className="chat-panel-subtitle">Ask about your documents & videos</span>
        </div>
        <button className="btn btn-ghost btn-icon" onClick={onClose} aria-label="Close chat panel">
          ✕
        </button>
      </div>

      {/* Messages */}
      <main className="chat-messages">
        {messages.map(msg => (
          <div key={msg.id} className={`chat-bubble-row ${msg.role}`}>
            <div className={`chat-bubble ${msg.role}`}>
              {msg.loading ? (
                <span className="typing-indicator">
                  <span /><span /><span />
                </span>
              ) : (
                <>
                  <p className="bubble-text">{msg.content}</p>
                  {msg.sources && msg.sources.length > 0 && (
                    <details className="sources-block">
                      <summary>{msg.sources.length} source{msg.sources.length > 1 ? 's' : ''}</summary>
                      <ul className="sources-list">
                        {msg.sources.map((src, i) => (
                          <li key={i} className="source-item">
                            <span className="source-type-badge">{src.type}</span>
                            <span className="source-title">{src.title}</span>
                            <span className="source-score">
                              {(src.relevance_score * 100).toFixed(0)}% match
                            </span>
                          </li>
                        ))}
                      </ul>
                    </details>
                  )}
                </>
              )}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </main>

      {/* Input bar */}
      <footer className="chat-input-bar">
        <textarea
          ref={inputRef}
          className="chat-input"
          rows={1}
          placeholder="Ask about your documents or videos…"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isLoading}
        />
        <button
          className="chat-send-btn"
          onClick={sendMessage}
          disabled={!input.trim() || isLoading}
          aria-label="Send"
        >
          ➤
        </button>
      </footer>
    </div>
  )
}

export default ChatPanel
