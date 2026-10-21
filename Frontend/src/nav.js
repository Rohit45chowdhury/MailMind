import { LayoutDashboard, ShieldAlert, FileText, PenLine, SpellCheck, Send, Settings } from 'lucide-react'

export const USER_NAME = 'Rohit'

export const nav = [
  { path: '/', label: 'Dashboard', title: 'Dashboard', desc: 'Your email tools in one place.', icon: LayoutDashboard },
  { path: '/spam', label: 'Spam Detection', title: 'Spam Detection', desc: 'Check whether an email is spam.', icon: ShieldAlert, tone: 'red', blurb: 'Check if an email is spam and see why.' },
  { path: '/summarize', label: 'Email Summarizer', title: 'Email Summarizer', desc: 'Get a short summary of a long email.', icon: FileText, tone: 'blue', blurb: 'Turn a long email into a short summary.' },
  { path: '/generate', label: 'Email Generator', title: 'Email Generator', desc: 'Write a complete email from a short brief.', icon: PenLine, tone: 'green', blurb: 'Write a full email from a short brief.' },
  { path: '/grammar', label: 'Grammar Checker', title: 'Grammar Checker', desc: 'Fix grammar, spelling and style.', icon: SpellCheck, tone: 'violet', blurb: 'Fix grammar and spelling in your text.' },
  { path: '/send', label: 'Send Email', title: 'Send Email', desc: 'Review and send an email.', icon: Send, tone: 'amber', blurb: 'Review and send an email from the app.' },
  { path: '/settings', label: 'Settings', title: 'Settings', desc: 'Appearance and connection details.', icon: Settings },
]

export const tones = {
  red: 'bg-red-50 text-red-600 border-red-100 dark:bg-red-500/10 dark:border-red-500/20',
  blue: 'bg-blue-50 text-blue-600 border-blue-100 dark:bg-blue-500/10 dark:border-blue-500/20',
  green: 'bg-emerald-50 text-emerald-600 border-emerald-100 dark:bg-emerald-500/10 dark:border-emerald-500/20',
  violet: 'bg-violet-50 text-violet-600 border-violet-100 dark:bg-violet-500/10 dark:border-violet-500/20',
  amber: 'bg-amber-50 text-amber-600 border-amber-100 dark:bg-amber-500/10 dark:border-amber-500/20',
}
