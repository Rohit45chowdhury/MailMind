import { Moon, Sun } from 'lucide-react'
import { API_URL } from '../api/axios.js'
import { useApp } from '../context/AppContext.jsx'
import GmailConnect from '../components/GmailConnect.jsx'

export default function Settings() {
  const { dark, toggleTheme } = useApp()
  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <GmailConnect />

      <section className="card">
        <h2 className="font-semibold text-slate-900 dark:text-white">Appearance</h2>
        <button className="btn-ghost mt-3" onClick={toggleTheme}>
          {dark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          Switch to {dark ? 'light' : 'dark'} theme
        </button>
      </section>

      <section className="card">
        <h2 className="font-semibold text-slate-900 dark:text-white">Backend connection</h2>
        <p className="mt-2 text-sm text-slate-500">API URL (set with <code>VITE_API_URL</code> in <code>.env</code>)</p>
        <code className="mt-1 block rounded-lg bg-slate-100 p-3 text-sm dark:bg-slate-950">{API_URL}</code>
        <p className="mt-3 text-sm text-slate-500">If requests fail with a network error, allow this app's origin in the backend's CORS settings. See the README.</p>
      </section>
    </div>
  )
}