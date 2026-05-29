export default function LoadingIndicator() {
  return (
    <div className="flex items-center gap-3 py-1 pl-12">
      <div className="flex gap-1">
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-brand-500 [animation-delay:-0.3s] dark:bg-brand-400" />
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-brand-400 [animation-delay:-0.15s] dark:bg-brand-500" />
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-brand-300 dark:bg-brand-600" />
      </div>
      <span className="text-sm font-medium text-zinc-500 dark:text-zinc-400">Preparing your answer…</span>
    </div>
  )
}
