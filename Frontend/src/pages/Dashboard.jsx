import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { BarChart3, Clock, Inbox, ShieldAlert, FileText, ChevronRight } from 'lucide-react'
import FeatureCard from '../components/FeatureCard.jsx'
import StatCard from '../components/StatCard.jsx'
import ErrorMessage from '../components/ErrorMessage.jsx'
import { EmptyState } from '../components/Field.jsx'
import { nav } from '../nav.js'
import { useAuth } from '../context/AuthContext.jsx'
import { getErrorMessage, getStats, resetStats } from '../api/axios.js'
import { timeAgo } from '../utils.js'

const tools = nav.filter((n) => n.tone)
const toolLabel = {
  spam: 'Spam Detection',
  summarize: 'Summarizer',
  generate: 'Email Generator',
  grammar: 'Grammar Check',
  draft: 'Approval Draft',
  calendar: 'Calendar Event',
}
const statusLabel = {
  spam: 'Spam',
  not_spam: 'Not spam',
  summarized: 'Summary ready',
  generated: 'Generated',
  checked: 'Checked',
  sent: 'Sent', // purani history ke liye rakha hai
  awaiting_approval: 'Awaiting approval',
  approved: 'Approved',
  rejected: 'Rejected',
  expired: 'Expired',
  created: 'Event created',
  no_meeting: 'No meeting found',
}

// Pending draft par click karne par kaunsa page khulega.
// NOTE: apne nav.js / routes ke asli path yahan daalo.
const resumePath = {
  draft: '/draft',
  calendar: '/calendar',
}

export default function Dashboard() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [s, setS] = useState(null)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    try { setS(await getStats()); setError('') } catch (e) { setError(getErrorMessage(e)) }
  }, [])

  // Load now, then refresh every 15 s and when the tab regains focus
  useEffect(() => {
    load()
    const t = setInterval(load, 15000)
    window.addEventListener('focus', load)
    return () => { clearInterval(t); window.removeEventListener('focus', load) }
  }, [load])

  const clear = async () => {
    try { await resetStats(); load() } catch (e) { setError(getErrorMessage(e)) }
  }

  // Pending draft ko wapas kholo: ?thread=<id> ke saath tool ke page par jao
  const resume = (a) => navigate(`${resumePath[a.tool]}?thread=${a.thread_id}`)

  const v = (n) => (s ? n : '…')
  const cards = [
    { icon: Inbox, label: 'Emails checked', value: v(s?.checked), tone: 'blue' },
    { icon: ShieldAlert, label: 'Spam detected', value: v(s?.spam), tone: 'red' },
    { icon: FileText, label: 'Summaries created', value: v(s?.summaries), tone: 'green' },
  ]
  const recent = s?.recent || []

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <div>
        <h2 className="text-2xl font-semibold text-slate-900 dark:text-white">Your inbox, under control.</h2>
        <p className="mt-1 text-slate-500 dark:text-slate-400">Welcome back, {user.name}. Pick a tool to get started.</p>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">{tools.map((t) => <FeatureCard key={t.path} item={t} />)}</div>
      <ErrorMessage message={error} />
      <div className="grid gap-6 lg:grid-cols-3">
        <section className="card" aria-labelledby="act">
          <h3 id="act" className="flex items-center gap-2 font-semibold text-slate-900 dark:text-white"><Clock className="h-4 w-4 text-indigo-600" /> Recent activity</h3>
          <p className="mb-3 text-xs text-slate-500">Your last actions in MailMind AI. {recent.length > 0 && <button onClick={clear} className="underline">Clear history</button>}</p>
          {recent.length === 0 ? <EmptyState icon={Clock} title="No activity yet" text="Run any tool and it will show up here." /> : (
            <ul className="divide-y divide-slate-100 dark:divide-slate-800">
              {recent.map((a, i) => {
                // sirf pending draft/calendar rows resume ho sakti hain (backend sirf unhi ko thread_id bhejta hai)
                const resumable = Boolean(a.thread_id && resumePath[a.tool])
                const content = (
                  <>
                    <div className="min-w-0">
                      <p className="font-medium">{toolLabel[a.tool] || a.tool}</p>
                      <p className="truncate text-xs text-slate-500">{a.detail} · {timeAgo(a.at)}</p>
                    </div>
                    <span className="flex shrink-0 items-center gap-1">
                      <span className="rounded-full bg-indigo-50 px-2 py-0.5 text-xs font-medium text-indigo-700 dark:bg-indigo-500/10 dark:text-indigo-300">{statusLabel[a.status] || a.status}</span>
                      {resumable && <ChevronRight className="h-4 w-4 text-slate-400" aria-hidden="true" />}
                    </span>
                  </>
                )
                return (
                  <li key={a.id || i}>
                    {resumable ? (
                      <button
                        type="button"
                        onClick={() => resume(a)}
                        title="Open this draft"
                        className="-mx-2 flex w-[calc(100%+1rem)] items-center justify-between gap-2 rounded-lg px-2 py-2.5 text-left text-sm hover:bg-slate-50 dark:hover:bg-slate-800/50"
                      >
                        {content}
                      </button>
                    ) : (
                      <div className="flex items-center justify-between gap-2 py-2.5 text-sm">{content}</div>
                    )}
                  </li>
                )
              })}
            </ul>
          )}
        </section>
        <section className="card" aria-labelledby="stats">
          <h3 id="stats" className="flex items-center gap-2 font-semibold text-slate-900 dark:text-white"><BarChart3 className="h-4 w-4 text-indigo-600" /> Quick stats</h3>
          <p className="mb-3 text-xs text-slate-500">Counted from your use of MailMind AI.</p>
          <div className="grid grid-cols-2 gap-3">
            {cards.map((c, i) => (
              <div key={c.label} className={i === cards.length - 1 && cards.length % 2 === 1 ? 'col-span-2' : ''}>
                <StatCard {...c} />
              </div>
            ))}
          </div>
        </section>
        <section className="card" aria-labelledby="qa">
          <h3 id="qa" className="mb-3 font-semibold text-slate-900 dark:text-white">Quick actions</h3>
          <ul className="space-y-2">
            {tools.map(({ path, label, icon: Icon }) => (
              <li key={path}><Link to={path} className="flex items-center gap-3 rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium hover:bg-slate-50 dark:border-slate-800 dark:hover:bg-slate-800">
                <Icon className="h-4 w-4 text-indigo-600" />{label}<ChevronRight className="ml-auto h-4 w-4 text-slate-400" />
              </Link></li>
            ))}
          </ul>
        </section>
      </div>
    </div>
  )
}