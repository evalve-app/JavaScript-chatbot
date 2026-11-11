// Thin API client. Vite proxies /api to the FastAPI server (see vite.config.ts).
const API_URL = ''

export type Source = { title: string; source_filename: string }

export type RunDetails = {
  request_id: string
  tools_called: string[]
  sources: Source[]
  duration_ms: number
  model_name: string
  kitaru_status?: string | null
  kitaru_session_id?: string | null
  kitaru_problem?: string | null
}

export type Member = { id: string; display_name: string }

export type ConversationSummary = { id: string; title: string; created_at: string; updated_at: string }

export type ChatMessage = {
  id: string
  role: 'user' | 'assistant'
  content: string
  details?: RunDetails | null
}

export type ConversationDetail = ConversationSummary & { messages: ChatMessage[] }

export type ChatResponse = {
  conversation_id: string
  message_id: string
  request_id: string
  response: string
  tools_called: string[]
  sources: Source[]
  duration_ms: number
  kitaru_status: string
  kitaru_session_id: string | null
}

export class ApiError extends Error {
  status: number
  body: Record<string, unknown>

  constructor(status: number, body: Record<string, unknown>) {
    const detail = typeof body.detail === 'string' ? body.detail : `Request failed (${status})`
    super(detail)
    this.status = status
    this.body = body
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...options.headers },
  })
  if (response.status === 204) return undefined as T
  const body = await response.json().catch(() => ({}))
  if (!response.ok) throw new ApiError(response.status, body)
  return body as T
}

export const api = {
  me: () => request<Member>('/api/auth/me'),
  login: (display_name: string) =>
    request<Member>('/api/auth/login', { method: 'POST', body: JSON.stringify({ display_name }) }),
  logout: () => request<void>('/api/auth/logout', { method: 'POST' }),
  listConversations: () => request<ConversationSummary[]>('/api/conversations'),
  getConversation: (id: string) => request<ConversationDetail>(`/api/conversations/${id}`),
  chat: (message: string, conversation_id: string | null) =>
    request<ChatResponse>('/api/chat', { method: 'POST', body: JSON.stringify({ message, conversation_id }) }),
}
