export default function Field({ label, id, as: Tag = 'input', className = '', children, ...rest }) {
  return (
    <div className={className}>
      <label htmlFor={id} className="label">{label}</label>
      <Tag id={id} className="input" {...rest}>{children}</Tag>
    </div>
  )
}

export function Toggle({ id, checked, onChange, label }) {
  return (
    <label htmlFor={id} className="flex cursor-pointer items-center gap-3 text-sm font-medium text-slate-700 dark:text-slate-300">
      <input id={id} type="checkbox" role="switch" checked={checked} onChange={(e) => onChange(e.target.checked)} className="peer sr-only" />
      <span className="relative h-6 w-11 rounded-full bg-slate-300 transition peer-checked:bg-indigo-600 peer-focus-visible:ring-2 peer-focus-visible:ring-indigo-500 peer-focus-visible:ring-offset-2 after:absolute after:left-0.5 after:top-0.5 after:h-5 after:w-5 after:rounded-full after:bg-white after:transition peer-checked:after:translate-x-5 dark:bg-slate-700" />
      {label}
    </label>
  )
}

export function EmptyState({ icon: Icon, title, text }) {
  return (
    <div className="flex h-full min-h-[240px] flex-col items-center justify-center rounded-lg bg-slate-50 p-6 text-center dark:bg-slate-950/50">
      <div className="rounded-full bg-slate-100 p-3 text-slate-400 dark:bg-slate-800"><Icon className="h-6 w-6" aria-hidden="true" /></div>
      <p className="mt-3 text-sm font-semibold text-slate-800 dark:text-slate-200">{title}</p>
      <p className="mt-1 max-w-xs text-sm text-slate-500 dark:text-slate-400">{text}</p>
    </div>
  )
}
