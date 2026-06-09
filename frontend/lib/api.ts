/** Backend URL: /api uses Next.js proxy (see next.config.js). */
export const API_URL = process.env.NEXT_PUBLIC_API_URL || '/api'

export interface ChatResponse {
  answer: string
  sources: string[]
  query_type: string
  retrieved_chunks: number
  highlighted_chunks: string[]
}

export interface HealthResponse {
  status: string
  index_ready: boolean
  llm_configured: boolean
  engine_ready: boolean
  init_error: string | null
  timestamp: string
}

function parseErrorDetail(detail: unknown): string {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail.map((d) => (typeof d === 'object' && d && 'msg' in d ? String(d.msg) : String(d))).join(', ')
  }
  return 'Request failed'
}

const REQUEST_TIMEOUT_MS = 180_000

async function apiFetch(path: string, init?: RequestInit): Promise<Response> {
  const url = `${API_URL}${path}`
  try {
    return await fetch(url, {
      ...init,
      cache: 'no-store',
      signal: init?.signal ?? AbortSignal.timeout(REQUEST_TIMEOUT_MS),
    })
  } catch (err) {
    if (err instanceof Error && err.name === 'TimeoutError') {
      throw new Error(
        'The assistant took too long to respond. Please wait a moment and try again.',
      )
    }
    throw new Error(
      'Unable to reach the assistant. Make sure the backend is running (scripts/start-backend.ps1) and try again.',
    )
  }
}

export interface ChatTurn {
  question: string
  answer: string
}

export async function sendMessage(
  question: string,
  conversationId: string,
  clientId: string,
  history: ChatTurn[] = [],
): Promise<ChatResponse> {
  const response = await apiFetch('/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      question,
      conversation_id: conversationId,
      client_id: clientId,
      history,
    }),
  })

  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(parseErrorDetail(body.detail) || 'Something went wrong. Please try again.')
  }

  return response.json()
}

export async function fetchHealth(): Promise<HealthResponse> {
  const response = await apiFetch('/health')
  if (!response.ok) {
    throw new Error('Service unavailable')
  }
  return response.json()
}
