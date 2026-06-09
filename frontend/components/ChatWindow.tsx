'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { BookOpen, GraduationCap, HelpCircle, MessageSquarePlus, Trash2 } from 'lucide-react'
import ChatMessage from './ChatMessage'
import MessageInput from './MessageInput'
import LoadingIndicator from './LoadingIndicator'
import ThemeToggle from './ThemeToggle'
import { sendMessage, ChatResponse, fetchHealth } from '../lib/api'
import {
  buildChatHistory,
  CONVERSATIONS_STORAGE_KEY,
  conversationsToPersist,
  createEmptyConversation,
  hasCompletedExchange,
  loadSavedConversations,
  StoredConversation,
  StoredMessage,
} from '../lib/conversations'
import { getDeviceId } from '../lib/device'

interface Message extends Omit<StoredMessage, 'timestamp'> {
  timestamp: Date
}

function toStoredMessage(message: Message): StoredMessage {
  return { ...message, timestamp: message.timestamp.toISOString() }
}

function fromStoredMessage(message: StoredMessage): Message {
  return { ...message, timestamp: new Date(message.timestamp) }
}

function fromStoredConversation(conv: StoredConversation): Conversation {
  return {
    ...conv,
    messages: conv.messages.map(fromStoredMessage),
  }
}

function toStoredConversation(conv: Conversation): StoredConversation {
  return {
    ...conv,
    messages: conv.messages.map(toStoredMessage),
  }
}

interface Conversation {
  id: string
  title: string
  messages: Message[]
  createdAt: string
}

const SUGGESTED_QUESTIONS = [
  'What courses does Masters Union offer?',
  'What are the admission requirements?',
  'Tell me about the faculty and directors',
  'What placement support is available?',
]

export default function ChatWindow() {
  const [savedConversations, setSavedConversations] = useState<Conversation[]>([])
  const [draftConversation, setDraftConversation] = useState<Conversation | null>(null)
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isInitialized, setIsInitialized] = useState(false)
  const [isOnline, setIsOnline] = useState<boolean | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const activeConversation =
    draftConversation?.id === activeConversationId
      ? draftConversation
      : savedConversations.find((conv) => conv.id === activeConversationId)
  const activeMessages = activeConversation?.messages ?? []
  const canChat = isOnline === true
  const isDraftActive = draftConversation?.id === activeConversationId

  const checkHealth = useCallback(async () => {
    try {
      const health = await fetchHealth()
      setIsOnline(health.engine_ready && health.llm_configured && health.index_ready)
    } catch {
      setIsOnline(false)
    }
  }, [])

  useEffect(() => {
    const saved = loadSavedConversations().map(fromStoredConversation)
    const draft = fromStoredConversation(createEmptyConversation())
    setSavedConversations(saved)
    setDraftConversation(draft)
    setActiveConversationId(draft.id)
    setIsInitialized(true)
  }, [])

  useEffect(() => {
    if (!isInitialized) return
    const stored = conversationsToPersist(savedConversations.map(toStoredConversation))
    window.localStorage.setItem(CONVERSATIONS_STORAGE_KEY, JSON.stringify(stored))
  }, [savedConversations, isInitialized])

  useEffect(() => {
    checkHealth()
    const interval = setInterval(checkHealth, 20000)
    return () => clearInterval(interval)
  }, [checkHealth])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [activeMessages.length, isLoading])

  const discardDraftIfUnused = () => {
    if (
      isDraftActive &&
      !hasCompletedExchange(activeMessages.map(toStoredMessage))
    ) {
      setDraftConversation(fromStoredConversation(createEmptyConversation()))
    }
  }

  const selectConversation = (id: string) => {
    if (id === activeConversationId) return
    discardDraftIfUnused()
    setActiveConversationId(id)
  }

  const startNewConversation = () => {
    if (isDraftActive && activeMessages.length === 0) return
    const fresh = fromStoredConversation(createEmptyConversation())
    setDraftConversation(fresh)
    setActiveConversationId(fresh.id)
  }

  const updateActiveConversation = (messages: Message[], title?: string) => {
    if (!activeConversationId) return

    if (draftConversation?.id === activeConversationId) {
      setDraftConversation((prev) =>
        prev
          ? {
              ...prev,
              messages,
              title: title ?? prev.title,
            }
          : prev,
      )
      return
    }

    setSavedConversations((prev) =>
      prev.map((conv) =>
        conv.id === activeConversationId
          ? { ...conv, messages, title: title ?? conv.title }
          : conv,
      ),
    )
  }

  const promoteDraftIfComplete = (messages: Message[], title?: string) => {
    if (!draftConversation || draftConversation.id !== activeConversationId) return
    if (!hasCompletedExchange(messages.map(toStoredMessage))) return

    const promoted: Conversation = {
      ...draftConversation,
      messages,
      title:
        title ??
        (draftConversation.title === 'New conversation'
          ? messages.find((m) => m.role === 'user')?.content.slice(0, 48) ?? draftConversation.title
          : draftConversation.title),
    }

    setSavedConversations((prev) => [promoted, ...prev.filter((c) => c.id !== promoted.id)])
    setDraftConversation(fromStoredConversation(createEmptyConversation()))
  }

  const deleteConversation = (id: string) => {
    setSavedConversations((prev) => prev.filter((c) => c.id !== id))

    if (activeConversationId === id) {
      const fresh = fromStoredConversation(createEmptyConversation())
      setDraftConversation(fresh)
      setActiveConversationId(fresh.id)
    }
  }

  const handleSendMessage = async (content: string) => {
    if (!content.trim() || !activeConversationId || !canChat) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content,
      timestamp: new Date(),
    }

    const updatedMessages = [...activeMessages, userMessage]
    const newTitle =
      activeConversation?.title === 'New conversation'
        ? content.slice(0, 48)
        : activeConversation?.title

    updateActiveConversation(updatedMessages, newTitle)
    setIsLoading(true)

    try {
      const history = buildChatHistory(activeMessages.map(toStoredMessage))
      const response: ChatResponse = await sendMessage(
        content,
        activeConversationId,
        getDeviceId(),
        history,
      )
      const withAssistant: Message[] = [
        ...updatedMessages,
        {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: response.answer,
          sources: response.sources,
          queryType: response.query_type,
          highlightedChunks: response.highlighted_chunks,
          timestamp: new Date(),
        },
      ]
      updateActiveConversation(withAssistant, newTitle)
      promoteDraftIfComplete(withAssistant, newTitle)
    } catch (err) {
      const errorMessage =
        err instanceof Error
          ? err.message
          : 'I was unable to process your request. Please try again in a moment.'
      const withError: Message[] = [
        ...updatedMessages,
        {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: errorMessage,
          timestamp: new Date(),
        },
      ]
      updateActiveConversation(withError, newTitle)
      promoteDraftIfComplete(withError, newTitle)
    } finally {
      setIsLoading(false)
    }
  }

  const status =
    isOnline === null
      ? {
          dot: 'bg-zinc-300 dark:bg-zinc-600',
          label: 'Connecting',
          pill: 'bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400',
        }
      : isOnline
        ? {
            dot: 'bg-emerald-500',
            label: 'Online',
            pill: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-400',
          }
        : {
            dot: 'bg-amber-500',
            label: 'Unavailable',
            pill: 'bg-amber-50 text-amber-800 dark:bg-amber-950 dark:text-amber-400',
          }

  return (
    <div className="flex h-[100dvh] overflow-hidden bg-zinc-50 dark:bg-zinc-950">
      <aside className="flex h-full w-full shrink-0 flex-col border-r border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-900 md:w-[300px]">
        <div className="shrink-0 border-b border-zinc-200 px-5 py-5 dark:border-zinc-800">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-brand-600 text-white shadow-soft">
              <GraduationCap size={22} strokeWidth={2} />
            </div>
            <div className="min-w-0 flex-1">
              <h1 className="text-[15px] font-bold tracking-tight text-zinc-900 dark:text-zinc-100">
                Masters&apos; Union
              </h1>
              <p className="text-[13px] font-semibold text-brand-600 dark:text-brand-400">Program Help</p>
            </div>
            <ThemeToggle />
          </div>

          <div className="mt-3 flex flex-wrap gap-1.5">
            <span className="inline-flex items-center gap-1 rounded-md bg-brand-50 px-2 py-1 text-[10px] font-bold uppercase tracking-wide text-brand-700 ring-1 ring-brand-100 dark:bg-brand-950 dark:text-brand-300 dark:ring-brand-900">
              <BookOpen size={10} />
              RAG Assistant
            </span>
            <span className="inline-flex items-center gap-1 rounded-md bg-zinc-100 px-2 py-1 text-[10px] font-bold uppercase tracking-wide text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400">
              <HelpCircle size={10} />
              Official docs
            </span>
          </div>

          <p className="mt-3 text-xs font-medium leading-relaxed text-zinc-500 dark:text-zinc-400">
            Your AI help desk for Masters&apos; Union — answers are retrieved from official program
            documents, not guessed. Chats are saved on this device only.
          </p>

          <div
            className={`mt-3 inline-flex items-center gap-2 rounded-full px-2.5 py-1 text-xs font-semibold ${status.pill}`}
          >
            <span className={`h-1.5 w-1.5 rounded-full ${status.dot}`} />
            {status.label}
          </div>
        </div>

        <div className="flex min-h-0 flex-1 flex-col">
          <div className="flex shrink-0 items-center justify-between px-4 pb-2 pt-3">
            <span className="sidebar-label">Conversations</span>
            <button
              type="button"
              onClick={startNewConversation}
              className="flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-semibold text-brand-600 transition hover:bg-brand-50 dark:text-brand-400 dark:hover:bg-brand-950"
            >
              <MessageSquarePlus size={15} strokeWidth={2} />
              New
            </button>
          </div>

          <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-3 pb-3">
            {savedConversations.length === 0 ? (
              <p className="px-2 py-4 text-center text-xs font-medium text-zinc-400 dark:text-zinc-500">
                No saved chats yet. Start typing to begin.
              </p>
            ) : (
              <div className="space-y-0.5">
                {savedConversations.map((conversation) => {
                  const active = conversation.id === activeConversationId
                  const preview =
                    conversation.messages[conversation.messages.length - 1]?.content ?? ''
                  return (
                    <div
                      key={conversation.id}
                      className={`group flex items-stretch rounded-xl transition-colors ${
                        active
                          ? 'bg-brand-50 dark:bg-brand-950'
                          : 'hover:bg-zinc-50 dark:hover:bg-zinc-800'
                      }`}
                    >
                      <button
                        type="button"
                        onClick={() => selectConversation(conversation.id)}
                        className={`min-w-0 flex-1 px-3 py-2.5 text-left ${
                          active
                            ? 'text-brand-900 dark:text-brand-100'
                            : 'text-zinc-700 dark:text-zinc-300'
                        }`}
                      >
                        <div className="truncate text-[13px] font-semibold leading-snug">
                          {conversation.title || 'New conversation'}
                        </div>
                        <div className="mt-0.5 truncate text-xs font-medium text-zinc-400">
                          {preview}
                        </div>
                      </button>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation()
                          deleteConversation(conversation.id)
                        }}
                        title="Delete conversation"
                        className="mr-1.5 shrink-0 self-center rounded-lg p-1.5 text-zinc-400 transition hover:bg-zinc-200 hover:text-red-600 dark:hover:bg-zinc-700 dark:hover:text-red-400"
                      >
                        <Trash2 size={14} strokeWidth={2} />
                      </button>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        </div>

        <div className="shrink-0 border-t border-zinc-200 px-5 py-3 dark:border-zinc-800">
          <p className="text-[11px] font-medium text-zinc-400 dark:text-zinc-500">
            Masters&apos; Union · Program Help
          </p>
        </div>
      </aside>

      <div className="flex min-h-0 min-w-0 flex-1 flex-col">
        <header className="z-10 shrink-0 border-b border-zinc-200 bg-white px-4 py-4 dark:border-zinc-800 dark:bg-zinc-900 sm:px-8">
          <div className="mx-auto flex max-w-3xl items-center justify-between gap-4">
            <div className="min-w-0">
              <h2 className="truncate text-lg font-bold tracking-tight text-zinc-900 dark:text-zinc-100">
                {activeConversation?.title || 'New conversation'}
              </h2>
              <p className="text-sm font-medium text-zinc-500 dark:text-zinc-400">
                Summaries from official Masters&apos; Union program documents
              </p>
            </div>
          </div>
        </header>

        {!canChat && isOnline !== null && (
          <div className="shrink-0 border-b border-amber-100 bg-amber-50 px-4 py-3 dark:border-amber-900/50 dark:bg-amber-950/50 sm:px-8">
            <p className="mx-auto max-w-3xl text-sm font-medium text-amber-900 dark:text-amber-200">
              The assistant is temporarily unavailable.{' '}
              <button
                type="button"
                onClick={checkHealth}
                className="font-semibold underline underline-offset-2 hover:text-amber-950 dark:hover:text-amber-100"
              >
                Retry
              </button>
            </p>
          </div>
        )}

        <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-4 py-6 sm:px-8">
          <div className="mx-auto max-w-3xl">
            {activeMessages.length === 0 ? (
              <div className="panel px-8 py-12 sm:px-12">
                <span className="inline-flex items-center gap-1.5 rounded-full bg-brand-50 px-3 py-1 text-xs font-bold text-brand-700 ring-1 ring-brand-100 dark:bg-brand-950 dark:text-brand-300 dark:ring-brand-900">
                  <HelpCircle size={14} />
                  Masters&apos; Union Help Center
                </span>
                <h2 className="mt-4 text-2xl font-bold tracking-tight text-zinc-900 dark:text-zinc-100 sm:text-[1.65rem]">
                  How can we help you?
                </h2>
                <p className="mt-3 max-w-lg text-[15px] leading-relaxed text-zinc-500 dark:text-zinc-400">
                  This is an AI assistant trained on Masters&apos; Union program documents. Ask about
                  admissions, courses, fees, faculty, placements, and campus life — answers arrive as
                  clear summaries backed by official sources.
                </p>
                <p className="mt-2 text-xs font-medium text-zinc-400 dark:text-zinc-500">
                  General questions unrelated to Masters&apos; Union cannot be answered.
                </p>
                {canChat && (
                  <div className="mt-8">
                    <p className="mb-3 text-xs font-bold uppercase tracking-[0.1em] text-zinc-400 dark:text-zinc-500">
                      Try asking
                    </p>
                    <div className="grid gap-2 sm:grid-cols-2">
                      {SUGGESTED_QUESTIONS.map((q) => (
                        <button
                          key={q}
                          type="button"
                          onClick={() => handleSendMessage(q)}
                          className="rounded-xl border border-zinc-200 bg-zinc-50/80 px-4 py-3 text-left text-[13px] font-medium leading-snug text-zinc-700 transition hover:border-brand-200 hover:bg-brand-50 hover:text-brand-900 dark:border-zinc-700 dark:bg-zinc-800/80 dark:text-zinc-300 dark:hover:border-brand-800 dark:hover:bg-brand-950 dark:hover:text-brand-200"
                        >
                          {q}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="space-y-10 pb-4">
                {activeMessages.map((message) => (
                  <ChatMessage key={message.id} message={message} />
                ))}
                {isLoading && <LoadingIndicator />}
              </div>
            )}
            <div ref={messagesEndRef} className="h-4" />
          </div>
        </div>

        <div className="shrink-0 border-t border-zinc-200 bg-white px-4 py-4 dark:border-zinc-800 dark:bg-zinc-900 sm:px-8">
          <div className="mx-auto max-w-3xl">
            <MessageInput
              onSendMessage={handleSendMessage}
              disabled={!canChat}
              sending={isLoading}
              placeholder={
                canChat
                  ? 'Ask about Masters\' Union programs, admissions, fees…'
                  : 'Assistant is unavailable…'
              }
            />
            <p className="mt-2 text-center text-xs font-medium text-zinc-400 dark:text-zinc-500">
              Enter to send · Shift + Enter for new line · Masters&apos; Union topics only
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
