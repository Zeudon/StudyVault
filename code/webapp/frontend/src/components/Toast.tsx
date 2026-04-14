import { createContext, useContext, useState, useCallback, useRef } from 'react'
import './Toast.css'

interface ToastItem {
  id: number
  type: 'success' | 'error'
  message: string
}

interface ToastContextValue {
  addToast: (t: Omit<ToastItem, 'id'>) => void
}

const ToastContext = createContext<ToastContextValue>({ addToast: () => {} })

export const useToast = () => useContext(ToastContext)

const DURATION_MS = 5000

const Toast: React.FC<{ item: ToastItem; onDismiss: (id: number) => void }> = ({ item, onDismiss }) => {
  const isSuccess = item.type === 'success'

  return (
    <div className={`toast toast-${item.type}`} role="alert">
      <div className={`toast-icon-wrap toast-icon-${item.type}`}>
        {isSuccess ? (
          <svg viewBox="0 0 20 20" fill="currentColor" width="18" height="18">
            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 00-1.414 0L8 12.586 4.707 9.293a1 1 0 00-1.414 1.414l4 4a1 1 0 001.414 0l8-8a1 1 0 000-1.414z" clipRule="evenodd" />
          </svg>
        ) : (
          <svg viewBox="0 0 20 20" fill="currentColor" width="18" height="18">
            <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
          </svg>
        )}
      </div>
      <div className="toast-body">
        <p className="toast-title">{isSuccess ? 'Success' : 'Error'}</p>
        <p className="toast-message">{item.message}</p>
      </div>
      <button className="toast-dismiss" onClick={() => onDismiss(item.id)} aria-label="Dismiss">
        <svg viewBox="0 0 20 20" fill="currentColor" width="14" height="14">
          <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
        </svg>
      </button>
      <div className={`toast-progress toast-progress-${item.type}`} style={{ animationDuration: `${DURATION_MS}ms` }} />
    </div>
  )
}

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<ToastItem[]>([])
  const counter = useRef(0)

  const dismiss = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  const addToast = useCallback(({ type, message }: Omit<ToastItem, 'id'>) => {
    const id = ++counter.current
    setToasts((prev) => [...prev, { id, type, message }])
    setTimeout(() => dismiss(id), DURATION_MS)
  }, [dismiss])

  return (
    <ToastContext.Provider value={{ addToast }}>
      {children}
      <div className="toast-container" aria-live="polite">
        {toasts.map((t) => (
          <Toast key={t.id} item={t} onDismiss={dismiss} />
        ))}
      </div>
    </ToastContext.Provider>
  )
}
