'use client'

import { useState, useRef, ChangeEvent, KeyboardEvent, useLayoutEffect, useCallback } from 'react'
import { ArrowUp } from 'lucide-react'

interface MessageInputProps {
  onSendMessage: (message: string) => void
  /** Disables typing (e.g. backend offline). */
  disabled?: boolean
  /** Disables send only while a reply is generating — typing still allowed. */
  sending?: boolean
  placeholder?: string
}

const MAX_HEIGHT = 160
const MIN_HEIGHT = 52

export default function MessageInput({
  onSendMessage,
  disabled,
  sending = false,
  placeholder,
}: MessageInputProps) {
  const [message, setMessage] = useState('')
  const [isMultiline, setIsMultiline] = useState(false)
  const [needsScroll, setNeedsScroll] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const singleLineHeightRef = useRef(MIN_HEIGHT)

  const syncTextareaSize = useCallback((value: string) => {
    const el = textareaRef.current
    if (!el) return

    el.style.height = 'auto'
    const scrollHeight = el.scrollHeight
    const nextHeight = Math.min(Math.max(scrollHeight, singleLineHeightRef.current), MAX_HEIGHT)

    el.style.height = `${nextHeight}px`

    const multiline = scrollHeight > singleLineHeightRef.current + 1
    const scroll = scrollHeight > MAX_HEIGHT

    setIsMultiline(multiline)
    setNeedsScroll(scroll)
    el.style.overflowY = scroll ? 'auto' : 'hidden'
  }, [])

  useLayoutEffect(() => {
    const el = textareaRef.current
    if (!el) return

    const saved = el.value
    el.value = 'A'
    el.style.height = 'auto'
    singleLineHeightRef.current = el.scrollHeight
    el.value = saved
    syncTextareaSize(saved)
  }, [syncTextareaSize])

  const canSend = Boolean(message.trim()) && !disabled && !sending

  const handleSubmit = () => {
    if (!canSend) return
    onSendMessage(message.trim())
    setMessage('')
    setIsMultiline(false)
    setNeedsScroll(false)
    requestAnimationFrame(() => {
      const el = textareaRef.current
      if (el) {
        el.style.height = `${singleLineHeightRef.current}px`
        el.style.overflowY = 'hidden'
      }
    })
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  const handleInputChange = (e: ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value
    setMessage(value)
    syncTextareaSize(value)
  }

  return (
    <div className="rounded-2xl bg-white shadow-input ring-1 ring-zinc-200/90 transition-shadow focus-within:shadow-[0_0_0_3px_rgba(37,99,235,0.12)] focus-within:ring-brand-500/40 dark:bg-zinc-900 dark:shadow-input-dark dark:ring-zinc-700 dark:focus-within:shadow-[0_0_0_3px_rgba(59,130,246,0.15)] dark:focus-within:ring-brand-500/30">
      <div className="flex items-end gap-2 px-3 py-2.5">
        <textarea
          ref={textareaRef}
          value={message}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          placeholder={placeholder ?? 'Ask a question…'}
          className={`min-h-[52px] max-h-40 flex-1 resize-none bg-transparent py-2.5 text-[15px] font-medium leading-relaxed text-zinc-900 placeholder:font-normal placeholder:text-zinc-400 focus:outline-none dark:text-zinc-100 dark:placeholder:text-zinc-500 ${
            isMultiline ? 'pr-1' : 'pr-0'
          } ${needsScroll ? 'overflow-y-auto' : 'overflow-y-hidden'}`}
          rows={1}
          disabled={disabled}
          aria-label="Message"
        />
        <button
          type="button"
          onClick={handleSubmit}
          disabled={!canSend}
          aria-label="Send message"
          className="mb-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-brand-600 text-white transition hover:bg-brand-700 disabled:bg-zinc-200 disabled:text-zinc-400 dark:disabled:bg-zinc-700 dark:disabled:text-zinc-500"
        >
          <ArrowUp size={18} strokeWidth={2.5} />
        </button>
      </div>
    </div>
  )
}
