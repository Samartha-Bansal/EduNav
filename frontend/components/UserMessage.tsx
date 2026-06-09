'use client'

import { useState } from 'react'

const COLLAPSE_CHAR_LIMIT = 320
const COLLAPSE_LINE_LIMIT = 5

interface UserMessageProps {
  content: string
}

export default function UserMessage({ content }: UserMessageProps) {
  const [expanded, setExpanded] = useState(false)
  const lineCount = content.split('\n').length
  const isLong =
    content.length > COLLAPSE_CHAR_LIMIT || lineCount > COLLAPSE_LINE_LIMIT

  return (
    <div className="flex min-w-0 max-w-[88%] justify-end sm:max-w-lg">
      <div className="min-w-0 max-w-full rounded-2xl rounded-br-md bg-brand-600 px-4 py-3 text-[15px] font-medium leading-relaxed text-white shadow-soft dark:bg-brand-500">
        <p
          className={`[overflow-wrap:anywhere] whitespace-pre-wrap ${
            isLong && !expanded ? 'line-clamp-5' : ''
          }`}
        >
          {content}
        </p>
        {isLong && (
          <button
            type="button"
            onClick={() => setExpanded((v) => !v)}
            className="mt-2 text-xs font-semibold text-white/85 underline underline-offset-2 hover:text-white"
          >
            {expanded ? 'Show less' : 'Show more'}
          </button>
        )}
      </div>
    </div>
  )
}
