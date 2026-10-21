import { Link } from 'react-router-dom'
import { ArrowRight } from 'lucide-react'
import { tones } from '../nav.js'

export default function FeatureCard({ item }) {
  const Icon = item.icon
  return (
    <Link to={item.path} className={`group flex flex-col rounded-xl border p-4 transition hover:shadow-md ${tones[item.tone]}`}>
      <span className="w-fit rounded-lg bg-white p-2 shadow-sm dark:bg-slate-900"><Icon className="h-5 w-5" aria-hidden="true" /></span>
      <h3 className="mt-3 font-semibold text-slate-900 dark:text-white">{item.label}</h3>
      <p className="mt-1 flex-1 text-sm text-slate-600 dark:text-slate-400">{item.blurb}</p>
      <ArrowRight className="mt-3 h-4 w-4 transition group-hover:translate-x-1" aria-hidden="true" />
    </Link>
  )
}
