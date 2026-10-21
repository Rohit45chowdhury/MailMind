import { useEffect } from 'react'
import { Loader2 } from 'lucide-react'

export default function ConfirmDialog({ open, title, children, confirmLabel, busy, onConfirm, onCancel }) {
  useEffect(() => {
    if (!open) return
    const onKey = (e) => e.key === 'Escape' && !busy && onCancel()
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open, busy, onCancel])
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4" onClick={() => !busy && onCancel()}>
      <div role="dialog" aria-modal="true" aria-labelledby="dlg-title" className="card w-full max-w-md" onClick={(e) => e.stopPropagation()}>
        <h2 id="dlg-title" className="text-lg font-semibold text-slate-900 dark:text-white">{title}</h2>
        <div className="mt-2 text-sm text-slate-600 dark:text-slate-400">{children}</div>
        <div className="mt-5 flex justify-end gap-2">
          <button className="btn-ghost" onClick={onCancel} disabled={busy}>Cancel</button>
          <button className="btn-primary" onClick={onConfirm} disabled={busy} autoFocus>
            {busy && <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />}{confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}
