import { Link } from 'react-router-dom'
import { BarChart3, Clock, Inbox, Send, ShieldAlert, FileText, ChevronRight } from 'lucide-react'
import FeatureCard from '../components/FeatureCard.jsx'
import StatCard from '../components/StatCard.jsx'
import { EmptyState } from '../components/Field.jsx'
import { nav, USER_NAME } from '../nav.js'
import { useApp } from '../context/AppContext.jsx'

const tools = nav.filter((n) => n.tone)
// SAMPLE DATA: illustrative only. The backend has no analytics endpoint.
const sample = [
  { icon: Inbox, label: 'Total emails', value: 24, tone: 'blue' },
  { icon: ShieldAlert, label: 'Spam detected', value: 5, tone: 'red' },
  { icon: FileText, label: 'Summaries created', value: 12, tone: 'green' },
  { icon: Send, label: 'Emails sent', value: 8, tone: 'violet' },
]

export default function Dashboard() {
  const { activity } = useApp()
  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <div>
        <h2 className="text-2xl font-semibold text-slate-900 dark:text-white">Your inbox, under control.</h2>
        <p className="mt-1 text-slate-500 dark:text-slate-400">Welcome back, {USER_NAME}. Pick a tool to get started.</p>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">{tools.map((t) => <FeatureCard key={t.path} item={t} />)}</div>
      <div className="grid gap-6 lg:grid-cols-3">
        <section className="card" aria-labelledby="act">
          <h3 id="act" className="flex items-center gap-2 font-semibold text-slate-900 dark:text-white"><Clock className="h-4 w-4 text-indigo-600" /> Recent activity</h3>
          <p className="mb-3 text-xs text-slate-500">Real results from this session. Cleared on reload.</p>
          {activity.length === 0 ? <EmptyState icon={Clock} title="No activity yet" text="Run any tool and its result will show up here." /> : (
            <ul className="divide-y divide-slate-100 dark:divide-slate-800">
              {activity.map((a) => (
                <li key={a.id} className="flex items-center justify-between gap-2 py-2.5 text-sm">
                  <div className="min-w-0"><p className="font-medium">{a.tool}</p><p className="truncate text-xs text-slate-500">{a.detail}</p></div>
                  <span className="shrink-0 rounded-full bg-indigo-50 px-2 py-0.5 text-xs font-medium text-indigo-700 dark:bg-indigo-500/10 dark:text-indigo-300">{a.status}</span>
                </li>
              ))}
            </ul>
          )}
        </section>
        <section className="card" aria-labelledby="stats">
          <h3 id="stats" className="flex items-center gap-2 font-semibold text-slate-900 dark:text-white"><BarChart3 className="h-4 w-4 text-indigo-600" /> Quick stats</h3>
          <p className="mb-3 text-xs text-amber-600 dark:text-amber-400">Sample data. Not connected to the backend.</p>
          <div className="grid grid-cols-2 gap-3">{sample.map((s) => <StatCard key={s.label} {...s} />)}</div>
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
