import { useEffect, useRef, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { ChevronDown, LogOut, Menu, Moon, Settings, Sun } from 'lucide-react'
import { nav } from '../nav.js'
import { useAuth } from '../context/AuthContext.jsx'
import { useApp } from '../context/AppContext.jsx'

export default function Header({ onMenu }) {
  const { pathname } = useLocation()
  const { dark, toggleTheme } = useApp()
  const { user, logout } = useAuth()
  const [menu, setMenu] = useState(false)
  const ref = useRef(null)
  const page = nav.find((n) => n.path === pathname) || nav[0]

  useEffect(() => {
    const close = (e) => ref.current && !ref.current.contains(e.target) && setMenu(false)
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [])

  return (
    <header className="sticky top-0 z-20 flex items-center gap-3 border-b border-slate-200 bg-white/90 px-4 py-3 backdrop-blur dark:border-slate-800 dark:bg-slate-900/90 sm:px-6">
      <button className="btn-ghost !px-2 lg:hidden" onClick={onMenu} aria-label="Open menu"><Menu className="h-5 w-5" /></button>
      <div className="min-w-0 flex-1">
        <h1 className="truncate text-lg font-semibold text-slate-900 dark:text-white">{page.title}</h1>
        <p className="hidden truncate text-sm text-slate-500 dark:text-slate-400 sm:block">{page.desc}</p>
      </div>
      <button className="btn-ghost !px-2" onClick={toggleTheme} aria-label={dark ? 'Switch to light theme' : 'Switch to dark theme'}>
        {dark ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
      </button>
      <div className="relative" ref={ref}>
        <button className="flex items-center gap-2 rounded-lg p-1 hover:bg-slate-100 dark:hover:bg-slate-800" onClick={() => setMenu((m) => !m)} aria-haspopup="menu" aria-expanded={menu}>
          <span className="flex h-8 w-8 items-center justify-center rounded-full bg-indigo-600 text-sm font-semibold text-white">{user.name[0].toUpperCase()}</span>
          <span className="hidden text-sm font-medium sm:block">{user.name}</span>
          <ChevronDown className="h-4 w-4 text-slate-400" />
        </button>
        {menu && (
          <div role="menu" className="card absolute right-0 mt-2 w-48 !p-1">
            <Link role="menuitem" to="/settings" onClick={() => setMenu(false)} className="flex items-center gap-2 rounded-md px-3 py-2 text-sm hover:bg-slate-100 dark:hover:bg-slate-800">
              <Settings className="h-4 w-4" /> Settings
            </Link>
            <button role="menuitem" onClick={logout} className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm hover:bg-slate-100 dark:hover:bg-slate-800">
              <LogOut className="h-4 w-4" /> Sign out
            </button>
          </div>
        )}
      </div>
    </header>
  )
}
