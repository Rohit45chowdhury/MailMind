import { useCallback, useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Mail, CalendarDays, CheckCircle2, AlertCircle, Circle } from 'lucide-react'
import {
  getGoogleStatus,
  getGoogleConnectUrl,
  disconnectGoogle,
  getErrorMessage,
} from '../api/axios.js'

// Messages for the ?gmail=... value the backend adds after the Google redirect
const MESSAGES = {
  connected: { ok: true, text: 'Google connected successfully.' },
  partial: { ok: false, text: 'Connected, but one permission was not granted. Connect again and tick every box to use all features.' },
  mismatch: { ok: false, text: 'Only the Google account that matches your login email can be connected. Choose the right account.' },
  denied: { ok: false, text: 'Permission was not granted. Allow access to continue.' },
  failed: { ok: false, text: 'Could not connect. Please try again.' },
  invalid: { ok: false, text: 'Your session expired. Please try again.' },
}

const FEATURES = {
  gmail: { label: 'Gmail', hint: 'Send emails after you approve them', Icon: Mail },
  calendar: { label: 'Google Calendar', hint: 'Add events after you approve them', Icon: CalendarDays },
}

/**
 * feature = 'all'      -> shows Gmail and Calendar rows (Settings page)
 * feature = 'gmail'    -> shows only the Gmail row
 * feature = 'calendar' -> shows only the Calendar row (Calendar page)
 */
export default function GmailConnect({ feature = 'all' }) {
  const [status, setStatus] = useState(null) // null = loading
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [params, setParams] = useSearchParams()
  const result = MESSAGES[params.get('gmail')]

  const keys = feature === 'all' ? ['gmail', 'calendar'] : [feature]

  const load = useCallback(async () => {
    try {
      setStatus(await getGoogleStatus())
    } catch (e) {
      setError(getErrorMessage(e))
      setStatus({})
    }
  }, [])

  useEffect(() => { load() }, [load])

  // Show the ?gmail=... result once, then clean the URL
  useEffect(() => {
    if (!result) return
    const t = setTimeout(() => setParams({}, { replace: true }), 6000)
    return () => clearTimeout(t)
  }, [result, setParams])

  const isOn = (key) => Boolean(status?.[key] ?? (key === 'gmail' ? status?.connected : false))
  const missing = keys.filter((k) => !isOn(k))
  const anyConnected = keys.some(isOn)

  const connect = async () => {
    setBusy(true); setError('')
    try {
      // Ask only for what is missing; 'all' when several features are missing
      const target = feature === 'all' ? 'all' : feature
      window.location.href = await getGoogleConnectUrl(target) // go to Google
    } catch (e) {
      setError(getErrorMessage(e)); setBusy(false)
    }
  }

  const disconnect = async () => {
    const ok = window.confirm('This removes Google access for both Gmail and Calendar. Continue?')
    if (!ok) return
    setBusy(true); setError('')
    try { await disconnectGoogle(); await load() } catch (e) { setError(getErrorMessage(e)) }
    setBusy(false)
  }

  const title = feature === 'all' ? 'Google connection' : `${FEATURES[feature].label} connection`
  const connectLabel =
    feature === 'all'
      ? missing.length === keys.length ? 'Connect Google' : 'Connect missing permissions'
      : `Connect ${FEATURES[feature].label}`

  return (
    <section className="card" aria-labelledby={`google-${feature}`}>
      <h3 id={`google-${feature}`} className="font-semibold text-slate-900 dark:text-white">
        {title}
      </h3>
      <p className="mb-3 mt-1 text-sm text-slate-500 dark:text-slate-400">
        Nothing is sent or added without your approval.
      </p>

      {result && (
        <p className={`mb-3 flex items-center gap-2 rounded-lg px-3 py-2 text-sm ${
          result.ok
            ? 'bg-emerald-50 text-emerald-800 dark:bg-emerald-500/10 dark:text-emerald-300'
            : 'bg-amber-50 text-amber-800 dark:bg-amber-500/10 dark:text-amber-300'
        }`}>
          {result.ok ? <CheckCircle2 className="h-4 w-4" /> : <AlertCircle className="h-4 w-4" />}
          {result.text}
        </p>
      )}
      {error && <p className="mb-3 text-sm text-red-600">{error}</p>}

      {status === null ? (
        <p className="text-sm text-slate-500">Loading…</p>
      ) : (
        <>
          <ul className="mb-4 space-y-2">
            {keys.map((k) => {
              const { label, hint, Icon } = FEATURES[k]
              const on = isOn(k)
              return (
                <li key={k} className="flex items-center justify-between gap-3 text-sm">
                  <span className="flex items-center gap-2">
                    <Icon className="h-4 w-4 text-indigo-600" />
                    <span>
                      <b>{label}</b>
                      <span className="block text-xs text-slate-500 dark:text-slate-400">{hint}</span>
                    </span>
                  </span>
                  <span className={`flex items-center gap-1 ${on ? 'text-emerald-600' : 'text-slate-400'}`}>
                    {on ? <CheckCircle2 className="h-4 w-4" /> : <Circle className="h-4 w-4" />}
                    {on ? 'Connected' : 'Not connected'}
                  </span>
                </li>
              )
            })}
          </ul>

          {anyConnected && status.email && (
            <p className="mb-3 text-sm text-slate-600 dark:text-slate-300">
              Account: <b>{status.email}</b>
            </p>
          )}

          <div className="flex flex-wrap gap-3">
            {missing.length > 0 && (
              <button onClick={connect} disabled={busy}
                className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-50">
                {busy ? 'Redirecting…' : connectLabel}
              </button>
            )}
            {anyConnected && (
              <button onClick={disconnect} disabled={busy}
                className="rounded-lg border border-slate-300 px-3 py-2 text-sm hover:bg-slate-50 disabled:opacity-50 dark:border-slate-700 dark:hover:bg-slate-800">
                Disconnect Google
              </button>
            )}
          </div>
        </>
      )}
    </section>
  )
}