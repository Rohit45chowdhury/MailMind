import { tones } from '../nav.js'

export default function StatCard({ icon: Icon, label, value, tone = 'blue' }) {
  return (
    <div className={`rounded-xl border p-4 ${tones[tone]}`}>
      <Icon className="h-5 w-5" aria-hidden="true" />
      <p className="mt-3 text-sm text-slate-600 dark:text-slate-400">{label}</p>
      <p className="text-2xl font-semibold text-slate-900 dark:text-white">{value}</p>
    </div>
  )
}
