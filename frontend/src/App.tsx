import { useCallback, useEffect, useState } from 'react'
import { api, ApiError } from './api'
import type { ChatMessage, ConversationSummary, Member } from './api'
import AccessGate from './components/AccessGate'
import ChatPanel from './components/ChatPanel'
import Sidebar from './components/Sidebar'

export default function App() {
  const [member, setMember] = useState<Member | null>(null)
  const [checkingSession, setCheckingSession] = useState(true)
  const [conversations, setConversations] = useState<ConversationSummary[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [sending, setSending] = useState(false)
  const [loadingConversation, setLoadingConversation] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [sidebarOpen, setSidebarOpen] = useState(false)

  const handleAuthError = useCallback((err: unknown) => {
    if (err instanceof ApiError && err.status === 401) {
      setMember(null)
      return true
    }
    return false
  }, [])

  const refreshConversations = useCallback(async () => {
    try {
      setConversations(await api.listConversations())
    } catch (err) {
      handleAuthError(err)
    }
  }, [handleAuthError])

  useEffect(() => {
    api
      .me()
      .then(setMember)
      .catch(() => setMember(null))
      .finally(() => setCheckingSession(false))
  }, [])

  useEffect(() => {
    if (member) refreshConversations()
  }, [member, refreshConversations])

  function startNewChat() {
    setActiveId(null)
    setMessages([])
    setError(null)
    setSidebarOpen(false)
  }

  async function openConversation(id: string) {
    setSidebarOpen(false)
    if (id === activeId) return
    setActiveId(id)
    setMessages([])
    setError(null)
    setLoadingConversation(true)
    try {
      const detail = await api.getConversation(id)
      setMessages(detail.messages)
    } catch (err) {
      if (!handleAuthError(err)) setError(err instanceof Error ? err.message : 'Could not load conversation.')
    } finally {
      setLoadingConversation(false)
    }
  }

  async function sendMessage(text: string) {
    setError(null)
    setSending(true)
    setMessages((prev) => [...prev, { id: `local-${Date.now()}`, role: 'user', content: text }])
    try {
      const result = await api.chat(text, activeId)
      setActiveId(result.conversation_id)
      setMessages((prev) => [
        ...prev,
        {
          id: result.message_id,
          role: 'assistant',
          content: result.response,
          details: {
            request_id: result.request_id,
            classification: result.classification,
            route: result.route,
            tools_called: result.tools_called,
            sources: result.sources,
            duration_ms: result.duration_ms,
            model_name: '',
            kitaru_status: result.kitaru_status,
            kitaru_session_id: result.kitaru_session_id,
          },
        },
      ])
    } catch (err) {
      if (handleAuthError(err)) return
      if (err instanceof ApiError && typeof err.body.conversation_id === 'string') {
        setActiveId(err.body.conversation_id)
      }
      const requestId = err instanceof ApiError && err.body.request_id ? ` (request ${err.body.request_id})` : ''
      setError(`${err instanceof Error ? err.message : 'Something went wrong.'}${requestId}`)
    } finally {
      setSending(false)
      refreshConversations()
    }
  }

  async function signOut() {
    await api.logout().catch(() => undefined)
    setMember(null)
    setConversations([])
    startNewChat()
  }

  if (checkingSession) return <div className="splash">Loading…</div>
  if (!member) return <AccessGate onSignedIn={setMember} />

  return (
    <div className={`app ${sidebarOpen ? 'sidebar-open' : ''}`}>
      <Sidebar
        member={member}
        conversations={conversations}
        activeId={activeId}
        onNewChat={startNewChat}
        onSelect={openConversation}
        onSignOut={signOut}
        onClose={() => setSidebarOpen(false)}
      />
      <ChatPanel
        messages={messages}
        sending={sending}
        loading={loadingConversation}
        error={error}
        onDismissError={() => setError(null)}
        onSend={sendMessage}
        onOpenSidebar={() => setSidebarOpen(true)}
      />
    </div>
  )
}
