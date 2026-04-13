import { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
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
const STORAGE_KEY = 'studyvault_chat_history'

const ChatPanel: React.FC<ChatPanelProps> = ({ isOpen, user, onClose }) => {
  const makeWelcome = (): Message => ({
    id: 'welcome',
    role: 'assistant',
    content: `Hi ${user?.first_name ?? 'there'}! Ask me anything about your uploaded documents and videos.`,
  })

  const [messages, setMessages] = useState<Message[]>(() => {
    try {
      const stored = sessionStorage.getItem(STORAGE_KEY)
      if (stored) return JSON.parse(stored) as Message[]
    } catch { /* ignore parse errors */ }
    return [makeWelcome()]
  })
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  // Persist messages to sessionStorage on every change (skip loading placeholders)
  useEffect(() => {
    const toStore = messages.filter(m => !m.loading)
    try {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(toStore))
    } catch { /* quota exceeded — non-fatal */ }
  }, [messages])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Focus input when panel opens
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 300)
    }
  }, [isOpen])

  const clearHistory = () => {
    sessionStorage.removeItem(STORAGE_KEY)
    setMessages([makeWelcome()])
  }

  const resetTextareaHeight = () => {
    if (inputRef.current) {
      inputRef.current.style.height = 'auto'
    }
  }

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
    resetTextareaHeight()
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
          <span className="chat-panel-subtitle">Ask about your documents &amp; videos</span>
        </div>
        <div className="chat-panel-actions">
          <button
            className="btn btn-ghost btn-sm"
            onClick={clearHistory}
            title="Clear chat history"
            aria-label="Clear chat history"
          >
            Clear
          </button>
          <button className="btn btn-ghost btn-icon" onClick={onClose} aria-label="Close chat panel">
            ✕
          </button>
        </div>
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
                  {msg.role === 'assistant' ? (
                    <div className="bubble-text bubble-markdown">
                      <ReactMarkdown
                        remarkPlugins={[remarkGfm]}
                        components={{
                          code({ className, children, ...props }) {
                            const isBlock = /language-/.test(className || '')
                            return isBlock
                              ? <pre className="md-code-block"><code className={className}>{children}</code></pre>
                              : <code className="md-code-inline" {...props}>{children}</code>
                          },
                          p({ children }) { return <p className="md-p">{children}</p> },
                          ul({ children }) { return <ul className="md-ul">{children}</ul> },
                          ol({ children }) { return <ol className="md-ol">{children}</ol> },
                          li({ children }) { return <li className="md-li">{children}</li> },
                          strong({ children }) { return <strong className="md-strong">{children}</strong> },
                          a({ href, children }) {
                            return <a href={href} target="_blank" rel="noopener noreferrer" className="md-link">{children}</a>
                          },
                        }}
                      >
                        {msg.content}
                      </ReactMarkdown>
                    </div>
                  ) : (
                    <p className="bubble-text">{msg.content}</p>
                  )}
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
          onChange={e => {
            setInput(e.target.value)
            e.target.style.height = 'auto'
            e.target.style.height = `${e.target.scrollHeight}px`
          }}
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
