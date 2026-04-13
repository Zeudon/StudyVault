import { Navigate } from 'react-router-dom'

// The chatbot is now a side panel — open it via the "Chat" button in the Navbar.
export default function ChatPage() {
  return <Navigate to="/library" replace />
}
