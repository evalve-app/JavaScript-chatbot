import type { RunDetails } from '../api'

export default function DeveloperDetails({ details }: { details: RunDetails }) {
  const rows: [string, string][] = [
    ['Tools called', details.tools_called.length ? details.tools_called.join(', ') : 'none'],
    ['Sources', details.sources.length ? details.sources.map((s) => s.title).join(', ') : 'none'],
    ['Duration', `${details.duration_ms.toLocaleString()} ms`],
    ['Request ID', details.request_id],
  ]
  if (details.model_name) rows.splice(3, 0, ['Model', details.model_name])
  if (details.kitaru_status) rows.push(['Kitaru', details.kitaru_status])
  if (details.kitaru_session_id) rows.push(['Kitaru session', details.kitaru_session_id])
  if (details.kitaru_problem) rows.push(['Kitaru problem', details.kitaru_problem])

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
