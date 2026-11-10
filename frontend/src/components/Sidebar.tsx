import type { ConversationSummary, Member } from '../api'

type Props = {
  member: Member
  conversations: ConversationSummary[]
  activeId: string | null
  onNewChat: () => void
  onSelect: (id: string) => void
  onSignOut: () => void
  onClose: () => void
}

export default function Sidebar({ member, conversations, activeId, onNewChat, onSelect, onSignOut, onClose }: Props) {
  return (
    <>
      <div className="sidebar-backdrop" onClick={onClose} aria-hidden="true" />
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="brand">
            <span className="brand-mark small" aria-hidden="true">{'{}'}</span>
            StudyBot
          </div>
          <button className="new-chat" onClick={onNewChat}>
            <span aria-hidden="true">+</span> New chat
          </button>
        </div>

        <nav className="conversation-list" aria-label="Previous conversations">
          {conversations.length === 0 && <p className="muted empty-list">No conversations yet.</p>}
          {conversations.map((c) => (
            <button
              key={c.id}
              className={`conversation ${c.id === activeId ? 'active' : ''}`}
              aria-current={c.id === activeId ? 'page' : undefined}
              onClick={() => onSelect(c.id)}
              title={c.title}
            >
              {c.title}
            </button>
          ))}
        </nav>

        <div className="sidebar-footer">
          <span className="avatar" aria-hidden="true">{member.display_name.slice(0, 1).toUpperCase()}</span>
          <span className="member-name">{member.display_name}</span>
          <button className="link-button" onClick={onSignOut}>Sign out</button>
        </div>
      </aside>
    </>
  )
}
