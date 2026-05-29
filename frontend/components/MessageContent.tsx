'use client'

function formatInline(text: string) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g)
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return (
        <strong key={i} className="font-semibold text-zinc-900 dark:text-zinc-100">
          {part.slice(2, -2)}
        </strong>
      )
    }
    return part
  })
}

export default function MessageContent({ content }: { content: string }) {
  const normalized = content.replace(/\r\n/g, '\n').replace(/\\n/g, '\n').trim()
  const blocks = normalized.split(/\n\n+/)

  return (
    <div className="space-y-4 text-[15px] leading-[1.7] text-zinc-700 dark:text-zinc-300">
      {blocks.map((block, bi) => {
        const lines = block.split('\n').filter((l) => l.trim())
        const isList =
          lines.length > 1 &&
          lines.every((l) => /^[\s]*[-*•]\s/.test(l) || /^[\s]*\d+\.\s/.test(l))

        if (isList) {
          return (
            <ul key={bi} className="list-none space-y-2 pl-0">
              {lines.map((line, li) => {
                const text = line
                  .replace(/^[\s]*[-*•]\s+/, '')
                  .replace(/^[\s]*\d+\.\s+/, '')
                  .trim()
                return (
                  <li key={li} className="flex gap-2.5">
                    <span className="mt-2.5 h-1.5 w-1.5 shrink-0 rounded-full bg-brand-500 dark:bg-brand-400" />
                    <span className="font-normal">{formatInline(text)}</span>
                  </li>
                )
              })}
            </ul>
          )
        }

        return (
          <p key={bi} className="font-normal whitespace-pre-wrap">
            {lines.map((line, li) => (
              <span key={li}>
                {formatInline(line)}
                {li < lines.length - 1 ? <br /> : null}
              </span>
            ))}
          </p>
        )
      })}
    </div>
  )
}
