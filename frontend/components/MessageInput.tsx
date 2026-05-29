'use client'

import { useState, useRef, ChangeEvent, KeyboardEvent } from 'react'
import { ArrowUp } from 'lucide-react'

interface MessageInputProps {
  onSendMessage: (message: string) => void
  disabled?: boolean
  placeholder?: string
}

export default function MessageInput({ onSendMessage, disabled, placeholder }: MessageInputProps) {
  const [message, setMessage] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const handleSubmit = () => {
    if (message.trim() && !disabled) {
      onSendMessage(message.trim())
      setMessage('')
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto'
      }
    }
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  const handleInputChange = (e: ChangeEvent<HTMLTextAreaElement>) => {
    setMessage(e.target.value)
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 160)}px`
    }
  }

  return (
    <div className="relative rounded-2xl bg-white shadow-input ring-1 ring-zinc-200/90 transition-shadow focus-within:shadow-[0_0_0_3px_rgba(37,99,235,0.12)] focus-within:ring-brand-500/40 dark:bg-zinc-900 dark:shadow-input-dark dark:ring-zinc-700 dark:focus-within:shadow-[0_0_0_3px_rgba(59,130,246,0.15)] dark:focus-within:ring-brand-500/30">
      <textarea
        ref={textareaRef}
        value={message}
        onChange={handleInputChange}
        onKeyDown={handleKeyDown}
        placeholder={placeholder ?? 'Ask a question…'}
        className="w-full resize-none bg-transparent px-4 py-3.5 pr-14 text-[15px] font-medium leading-relaxed text-zinc-900 placeholder:font-normal placeholder:text-zinc-400 focus:outline-none min-h-[52px] max-h-40 dark:text-zinc-100 dark:placeholder:text-zinc-500"
        rows={1}
        disabled={disabled}
        aria-label="Message"
      />
      <button
        type="button"
        onClick={handleSubmit}
        disabled={!message.trim() || disabled}
        aria-label="Send message"
        className="absolute bottom-2.5 right-2.5 flex h-9 w-9 items-center justify-center rounded-xl bg-brand-600 text-white transition hover:bg-brand-700 disabled:bg-zinc-200 disabled:text-zinc-400 dark:disabled:bg-zinc-700 dark:disabled:text-zinc-500"
      >
        <ArrowUp size={18} strokeWidth={2.5} />
      </button>
    </div>
  )
}
