import { NavLink } from 'react-router-dom'
import { X } from 'lucide-react'
import { nav } from '../nav.js'

export default function Sidebar({ open, onClose }) {
  return (
    <>
      {open && <div className="fixed inset-0 z-30 bg-slate-900/60 lg:hidden" onClick={onClose} aria-hidden="true" />}
      <aside className={`fixed inset-y-0 left-0 z-40 flex w-64 flex-col bg-navy-900 p-4 transition-transform lg:sticky lg:top-0 lg:h-screen lg:translate-x-0 ${open ? 'translate-x-0' : '-translate-x-full'}`}>
        <div className="mb-6 flex items-center gap-3 px-1">
          <img src="/logo.jpg" alt="" className="h-10 w-10 rounded-lg bg-white object-cover p-0.5" />
          <div>
            <p className="font-semibold text-white">MailMind AI</p>
            <p className="text-xs text-slate-400">Your Inbox, Intelligently Managed.</p>
          </div>
          <button className="ml-auto rounded p-1 text-slate-400 hover:text-white lg:hidden" onClick={onClose} aria-label="Close menu"><X className="h-5 w-5" /></button>
        </div>
        <nav aria-label="Main" className="flex flex-col gap-1">
          {nav.map(({ path, label, icon: Icon }) => (
            <NavLink key={path} to={path} end={path === '/'} onClick={onClose}
              className={({ isActive }) => `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition ${isActive ? 'bg-indigo-600 text-white shadow' : 'text-slate-300 hover:bg-white/10 hover:text-white'}`}>
              <Icon className="h-5 w-5" aria-hidden="true" />{label}
            </NavLink>
          ))}
        </nav>
      </aside>
    </>
  )
}
