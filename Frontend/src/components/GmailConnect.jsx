import { useCallback, useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Mail, CheckCircle2, AlertCircle } from 'lucide-react'
import { getGmailStatus, getGmailConnectUrl, disconnectGmail, getErrorMessage } from '../api/axios.js'

const MESSAGES = {
  connected: { ok: true, text: 'Gmail connect ho gaya.' },
  mismatch: { ok: false, text: 'Login email wala Gmail hi connect ho sakta hai. Sahi account chuno.' },
  denied: { ok: false, text: 'Permission nahi di gayi. Mail bhejne ke liye Allow karna zaroori hai.' },
  failed: { ok: false, text: 'Connect nahi ho paya. Dobara try karo.' },
  invalid: { ok: false, text: 'Session expire ho gaya. Dobara try karo.' },
}

export default function GmailConnect() {
  const [status, setStatus] = useState(null)   // null = loading
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [params, setParams] = useSearchParams()
  const result = MESSAGES[params.get('gmail')]

  const load = useCallback(async () => {
    try { setStatus(await getGmailStatus()) } catch (e) { setError(getErrorMessage(e)) }
  }, [])

  useEffect(() => { load() }, [load])

  // ?gmail=... ek baar dikhao, phir URL saaf kar do
  useEffect(() => {
    if (!result) return
    const t = setTimeout(() => setParams({}, { replace: true }), 6000)
    return () => clearTimeout(t)
  }, [result, setParams])

  const connect = async () => {
    setBusy(true); setError('')
    try {
      window.location.href = await getGmailConnectUrl()   // Google pe le jao
    } catch (e) {
      setError(getErrorMessage(e)); setBusy(false)
    }
  }

  const disconnect = async () => {
    setBusy(true); setError('')
    try { await disconnectGmail(); await load() } catch (e) { setError(getErrorMessage(e)) }
    setBusy(false)
  }

  return (
    <section className="card" aria-labelledby="gmail">
      <h3 id="gmail" className="flex items-center gap-2 font-semibold text-slate-900 dark:text-white">
        <Mail className="h-4 w-4 text-indigo-600" /> Gmail connection
      </h3>
      <p className="mb-3 mt-1 text-sm text-slate-500 dark:text-slate-400">
        Mail aapke apne Gmail se jaati hai. Iske liye ek baar Gmail connect karna padta hai.
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
      ) : status.connected ? (
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="flex items-center gap-2 text-sm">
            <CheckCircle2 className="h-4 w-4 text-emerald-600" />
            Connected: <b>{status.email}</b>
          </p>
          <button onClick={disconnect} disabled={busy}
            className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm hover:bg-slate-50 disabled:opacity-50 dark:border-slate-700 dark:hover:bg-slate-800">
            Disconnect
          </button>
        </div>
      ) : (
        <button onClick={connect} disabled={busy}
          className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-50">
          {busy ? 'Redirecting…' : 'Connect Gmail'}
        </button>
      )}
    </section>
  )
}