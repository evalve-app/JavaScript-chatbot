import { useEffect, useRef } from 'react'
import type { ChatMessage } from '../api'
import ChatInput from './ChatInput'
import Message from './Message'

const SUGGESTIONS = [
  'Explain JavaScript closures.',
  'Help me debug this JavaScript function.',
  'Write a JavaScript function to flatten an array.',
  'Quiz me on JavaScript promises.',
]

type Props = {
  messages: ChatMessage[]
  sending: boolean
  loading: boolean
  error: string | null
  onDismissError: () => void
  onSend: (text: string) => void
  onOpenSidebar: () => void
}

export default function ChatPanel({ messages, sending, loading, error, onDismissError, onSend, onOpenSidebar }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages.length, sending])

  const isEmpty = messages.length === 0 && !loading

  return (
    <main className="chat-panel">
      <header className="mobile-header">
        <button className="icon-button" onClick={onOpenSidebar} aria-label="Open conversations">
          ☰
        </button>
        <span className="brand">StudyBot</span>
      </header>

      <div className="chat-scroll">
        <div className="chat-column">
          {isEmpty && (
            <div className="empty-state">
              <div className="brand-mark" aria-hidden="true">{'{}'}</div>
              <h1>StudyBot</h1>
              <p className="muted">Your JavaScript programming assistant.</p>
              <div className="suggestions">
                {SUGGESTIONS.map((s) => (
                  <button key={s} className="suggestion" onClick={() => onSend(s)} disabled={sending}>
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {loading && <p className="muted center">Loading conversation…</p>}

          {messages.map((m) => (
            <Message key={m.id} message={m} />
          ))}

          {sending && (
            <div className="message assistant">
              <div className="assistant-avatar" aria-hidden="true">{'{}'}</div>
              <div className="typing" aria-label="StudyBot is thinking">
                <span />
                <span />
                <span />
              </div>
            </div>
          )}

          {error && (
            <div className="error-banner" role="alert">
              <span>{error}</span>
              <button className="link-button" onClick={onDismissError}>Dismiss</button>
            </div>
          )}
          <div ref={bottomRef} />
        </div>
      </div>

      <ChatInput disabled={sending} onSend={onSend} />
    </main>
  )
}
