import { Loader2 } from 'lucide-react'

export default function LoadingSpinner({ label = 'Loading…', className = '' }) {
  return (
    <div role="status" className={`flex items-center justify-center gap-2 text-sm text-slate-500 dark:text-slate-400 ${className}`}>
      <Loader2 className="h-5 w-5 animate-spin text-indigo-600" aria-hidden="true" />
      <span>{label}</span>
    </div>
  )
}
