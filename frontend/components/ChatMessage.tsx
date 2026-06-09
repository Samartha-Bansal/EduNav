'use client'

import { useState } from 'react'
import { BookOpen, ChevronDown, ChevronUp, FileText, Sparkles } from 'lucide-react'
import MessageContent from './MessageContent'
import UserMessage from './UserMessage'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources?: string[]
  queryType?: string
  highlightedChunks?: string[]
  timestamp: Date
}

interface ChatMessageProps {
  message: Message
}

export default function ChatMessage({ message }: ChatMessageProps) {
  const [showSources, setShowSources] = useState(false)
  const isUser = message.role === 'user'

  if (isUser) {
    return (
      <div className="flex justify-end">
        <UserMessage content={message.content} />
      </div>
    )
  }

  const hasSources = (message.sources?.length ?? 0) > 0 || (message.highlightedChunks?.length ?? 0) > 0
  const isRefusal = message.queryType === 'out_of_scope'

  return (
    <div className="flex gap-3.5">
      <div
        className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl ${
          isRefusal
            ? 'bg-amber-50 text-amber-600 dark:bg-amber-950 dark:text-amber-400'
            : 'bg-brand-50 text-brand-600 dark:bg-brand-950 dark:text-brand-400'
        }`}
      >
        <Sparkles size={17} strokeWidth={2} />
      </div>
      <div className="min-w-0 flex-1 space-y-3">
        <div
          className={`max-w-3xl rounded-2xl border px-5 py-4 ${
            isRefusal
              ? 'border-amber-200/90 bg-amber-50/50 dark:border-amber-900/60 dark:bg-amber-950/40'
              : 'panel'
          }`}
        >
          <MessageContent content={message.content} />
        </div>

        {message.queryType && message.queryType !== 'informational' && (
          <span className="inline-block text-xs font-semibold capitalize text-zinc-400 dark:text-zinc-500">
            {message.queryType.replace(/_/g, ' ')}
          </span>
        )}

        {hasSources && (
          <div className="max-w-3xl overflow-hidden rounded-xl border border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-900">
            <button
              type="button"
              onClick={() => setShowSources(!showSources)}
              className="flex w-full items-center gap-2.5 px-4 py-3 text-left text-sm font-semibold text-zinc-600 transition hover:bg-zinc-50 dark:text-zinc-400 dark:hover:bg-zinc-800"
            >
              <BookOpen size={16} className="text-brand-500 dark:text-brand-400" />
              <span className="flex-1">
                {message.sources?.length ?? 0} source{(message.sources?.length ?? 0) !== 1 ? 's' : ''}
              </span>
              {showSources ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            </button>

            {showSources && (
              <div className="space-y-4 border-t border-zinc-100 px-4 pb-4 pt-3 dark:border-zinc-800">
                {message.sources && message.sources.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {message.sources.map((source, index) => (
                      <span
                        key={index}
                        className="inline-flex items-center gap-1.5 rounded-lg bg-zinc-50 px-2.5 py-1.5 text-xs font-medium text-zinc-600 ring-1 ring-zinc-200/80 dark:bg-zinc-800 dark:text-zinc-300 dark:ring-zinc-700"
                      >
                        <FileText size={12} className="text-zinc-400 dark:text-zinc-500" />
                        {source}
                      </span>
                    ))}
                  </div>
                )}

                {message.highlightedChunks && message.highlightedChunks.length > 0 && (
                  <div className="space-y-2">
                    {message.highlightedChunks.map((chunk, index) => (
                      <blockquote
                        key={index}
                        className="border-l-2 border-brand-300 bg-brand-50/50 px-3 py-2 text-xs font-medium leading-relaxed text-zinc-600 dark:border-brand-700 dark:bg-brand-950/50 dark:text-zinc-400"
                      >
                        {chunk}
                      </blockquote>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
