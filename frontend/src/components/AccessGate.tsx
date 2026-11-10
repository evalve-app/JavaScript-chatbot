import { useState } from 'react'
import type { FormEvent } from 'react'
import { api } from '../api'
import type { Member } from '../api'

type Props = { onSignedIn: (member: Member) => void }

export default function AccessGate({ onSignedIn }: Props) {
  const [displayName, setDisplayName] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      onSignedIn(await api.login(displayName.trim()))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Sign-in failed.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="gate">
      <form className="gate-card" onSubmit={handleSubmit}>
        <div className="brand-mark" aria-hidden="true">{'{}'}</div>
        <h1>StudyBot</h1>
        <p className="muted">Your JavaScript programming assistant.</p>

        <label>
          Display name
          <input
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            maxLength={50}
            autoComplete="nickname"
            required
          />
        </label>

        {error && <p className="form-error" role="alert">{error}</p>}

        <button className="primary" type="submit" disabled={submitting || !displayName.trim()}>
          {submitting ? 'Signing in…' : 'Continue'}
        </button>
        <p className="fine-print">Your chats are saved under this name. Use the same name each time to see them.</p>
      </form>
    </div>
  )
}
