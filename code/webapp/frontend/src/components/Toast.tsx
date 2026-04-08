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

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<ToastItem[]>([])
  const counter = useRef(0)

  const addToast = useCallback(({ type, message }: Omit<ToastItem, 'id'>) => {
    const id = ++counter.current
    setToasts((prev) => [...prev, { id, type, message }])
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 5000)
  }, [])

  return (
    <ToastContext.Provider value={{ addToast }}>
      {children}
      <div className="toast-container">
        {toasts.map((t) => (
          <div key={t.id} className={`toast toast-${t.type}`}>
            {t.type === 'success' ? '✓' : '✕'} {t.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}
