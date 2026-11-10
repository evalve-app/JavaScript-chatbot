import type { RunDetails } from '../api'

export default function DeveloperDetails({ details }: { details: RunDetails }) {
  const c = details.classification
  const rows: [string, string][] = [
    ['Scope', c?.scope ?? '—'],
    ['Intent', c?.intent ?? '—'],
    ['Language', c?.language ?? '—'],
    ['Route', details.route ?? '—'],
    ['Tools called', details.tools_called.length ? details.tools_called.join(', ') : 'none'],
    ['Sources', details.sources.length ? details.sources.map((s) => s.title).join(', ') : 'none'],
    ['Duration', `${details.duration_ms.toLocaleString()} ms`],
    ['Request ID', details.request_id],
  ]
  if (details.model_name) rows.splice(7, 0, ['Model', details.model_name])

  return (
    <details className="dev-details">
      <summary>Developer details</summary>
      <dl>
        {rows.map(([label, value]) => (
          <div key={label} className="dev-row">
            <dt>{label}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
    </details>
  )
}
