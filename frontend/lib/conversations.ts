export interface StoredMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources?: string[]
  queryType?: string
  highlightedChunks?: string[]
  timestamp: string
}

export interface StoredConversation {
  id: string
  title: string
  messages: StoredMessage[]
  createdAt: string
}

export const CONVERSATIONS_STORAGE_KEY = 'edunavigator_conversations'

export function createConversationId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`
}

export function createEmptyConversation(): StoredConversation {
  return {
    id: createConversationId(),
    title: 'New conversation',
    messages: [],
    createdAt: new Date().toISOString(),
  }
}

/** A conversation is saved only after at least one user message and one assistant reply. */
export function hasCompletedExchange(messages: StoredMessage[]): boolean {
  const hasUser = messages.some((m) => m.role === 'user')
  const hasAssistant = messages.some((m) => m.role === 'assistant')
  return hasUser && hasAssistant
}

export function loadSavedConversations(): StoredConversation[] {
  if (typeof window === 'undefined') return []

  const raw = window.localStorage.getItem(CONVERSATIONS_STORAGE_KEY)
  if (!raw) return []

  try {
    const parsed = JSON.parse(raw) as StoredConversation[]
    if (!Array.isArray(parsed)) return []
    return parsed.filter(
      (c) => c && typeof c.id === 'string' && hasCompletedExchange(c.messages),
    )
  } catch {
    return []
  }
}

export function conversationsToPersist(conversations: StoredConversation[]): StoredConversation[] {
  return conversations.filter((c) => hasCompletedExchange(c.messages))
}

export function buildChatHistory(
  messages: StoredMessage[],
  maxTurns = 3,
): { question: string; answer: string }[] {
  const turns: { question: string; answer: string }[] = []
  let pendingQuestion: string | null = null

  for (const msg of messages) {
    if (msg.role === 'user') {
      pendingQuestion = msg.content
    } else if (msg.role === 'assistant' && pendingQuestion) {
      turns.push({ question: pendingQuestion, answer: msg.content })
      pendingQuestion = null
    }
  }

  return turns.slice(-maxTurns)
}
