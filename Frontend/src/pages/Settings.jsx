import { useState } from 'react'
import { Moon, Sun } from 'lucide-react'
import { API_URL, updateProfile, getErrorMessage } from '../api/axios.js'
import { useApp } from '../context/AppContext.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import GmailConnect from '../components/GmailConnect.jsx'

export default function Settings() {
  const { dark, toggleTheme } = useApp()
  const { user } = useAuth()
  const [name, setName] = useState(user?.name || '')
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState('')

  const saveName = async (e) => {
    e.preventDefault()
    const clean = name.trim()
    if (!clean) return
    setSaving(true)
    setMsg('')
    try {
      await updateProfile({ name: clean })
      window.location.reload() // reloads user data so the new name shows everywhere
    } catch (err) {
      setMsg(getErrorMessage(err))
      setSaving(false)
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <section className="card">
        <h2 className="font-semibold text-slate-900 dark:text-white">Profile</h2>
        <p className="mt-1 text-sm text-slate-500">
          This name is shown on your dashboard and used as the sender name in emails.
        </p>
        <form onSubmit={saveName} className="mt-3 flex flex-wrap gap-3">
          <input
            className="input w-full sm:w-72"
            value={name}
            onChange={(e) => setName(e.target.value)}
            maxLength={60}
            placeholder="Your name"
            aria-label="Display name"
          />
          <button className="btn-primary" disabled={saving || !name.trim() || name.trim() === user?.name}>
            {saving ? 'Saving…' : 'Save name'}
          </button>
        </form>
        {msg && <p className="mt-2 text-sm text-red-600">{msg}</p>}
      </section>

      {/* Shows both Gmail and Google Calendar rows with one Connect button */}
      <GmailConnect feature="all" />

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