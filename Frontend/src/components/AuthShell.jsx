import { ShieldCheck, FileText, PenLine } from 'lucide-react'

const points = [
  { icon: ShieldCheck, text: 'Catch spam before you open it' },
  { icon: FileText, text: 'Summarize long emails in seconds' },
  { icon: PenLine, text: 'Write and fix emails with AI' },
]

export default function AuthShell({ title, subtitle, children, footer }) {
  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <aside className="hidden flex-col justify-between bg-navy-900 p-10 lg:flex">
        <div className="flex items-center gap-3">
          <img src="/logo.jpg" alt="" className="h-11 w-11 rounded-lg bg-white object-cover p-0.5" />
          <span className="text-lg font-semibold text-white">MailMind AI</span>
        </div>
        <div>
          <h2 className="text-3xl font-semibold text-white">Your inbox, under control.</h2>
          <ul className="mt-6 space-y-4">
            {points.map(({ icon: Icon, text }) => (
              <li key={text} className="flex items-center gap-3 text-slate-300">
                <span className="rounded-lg bg-white/10 p-2 text-indigo-300"><Icon className="h-4 w-4" /></span>{text}
              </li>
            ))}
          </ul>
        </div>
        <p className="text-xs text-slate-500">Your Inbox, Intelligently Managed.</p>
      </aside>
      <main className="flex items-center justify-center p-6">
        <div className="w-full max-w-md">
          <div className="mb-6 flex items-center gap-2 lg:hidden">
            <img src="/logo.jpg" alt="" className="h-9 w-9 rounded-lg object-cover" />
            <span className="font-semibold text-slate-900 dark:text-white">MailMind AI</span>
          </div>
          <h1 className="text-2xl font-semibold text-slate-900 dark:text-white">{title}</h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{subtitle}</p>
          <div className="mt-6">{children}</div>
          <p className="mt-6 text-center text-sm text-slate-500 dark:text-slate-400">{footer}</p>
        </div>
      </main>
    </div>
  )
}
