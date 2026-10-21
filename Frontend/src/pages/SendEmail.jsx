import { useState } from 'react'
import { useLocation } from 'react-router-dom'
import { CheckCircle2, Send } from 'lucide-react'
import Field, { Toggle } from '../components/Field.jsx'
import ErrorMessage from '../components/ErrorMessage.jsx'
import ConfirmDialog from '../components/ConfirmDialog.jsx'
import useRequest from '../hooks/useRequest.js'
import { sendEmail } from '../api/axios.js'
import { useApp } from '../context/AppContext.jsx'

export default function SendEmail() {
  const { state } = useLocation()
  const { addActivity } = useApp()
  const [f, setF] = useState({ to: '', cc: '', bcc: '', subject: state?.subject || '', body: state?.body || '', sender_name: '' })
  const [html, setHtml] = useState(false)
  const [confirm, setConfirm] = useState(false)
  const { loading, error, data, run, fail, reset } = useRequest(sendEmail)
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })

  const review = (e) => {
    e.preventDefault()
    if (!f.to.includes('@')) return fail('Enter a valid recipient email address.')
    if (!f.subject.trim() || !f.body.trim()) return fail('Enter a subject and a message.')
    reset()
    setConfirm(true)
  }

  const send = async () => {
    const res = await run({
      to: f.to.trim(), subject: f.subject.trim(), body: f.body,
      cc: f.cc.trim() || null, bcc: f.bcc.trim() || null, html,
      sender_name: f.sender_name.trim() || null,
    })
    setConfirm(false)
    if (res) {
      addActivity('Send Email', f.to, 'Sent')
      setF({ to: '', cc: '', bcc: '', subject: '', body: '', sender_name: f.sender_name })
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      {state?.body && <p className="rounded-lg bg-indigo-50 p-3 text-sm text-indigo-800 dark:bg-indigo-500/10 dark:text-indigo-300">This draft came from another tool. Review it before you send.</p>}
      <form onSubmit={review} className="card space-y-4" noValidate>
        <Field id="to" label="To" type="email" placeholder="recipient@example.com" value={f.to} onChange={set('to')} />
        <div className="grid gap-4 sm:grid-cols-2">
          <Field id="cc" label="CC (optional)" value={f.cc} onChange={set('cc')} />
          <Field id="bcc" label="BCC (optional)" value={f.bcc} onChange={set('bcc')} />
        </div>
        <Field id="subject" label="Subject" placeholder="Meeting Confirmation" value={f.subject} onChange={set('subject')} />
        <Field id="body" as="textarea" rows={10} label={html ? 'Email body (HTML)' : 'Email body'} value={f.body} onChange={set('body')} />
        <div className="flex flex-wrap items-end gap-4">
          <Field id="sender_name" label="Sender name (optional)" className="w-56" value={f.sender_name} onChange={set('sender_name')} />
          <Toggle id="html" checked={html} onChange={setHtml} label="HTML mode" />
        </div>
        <ErrorMessage message={error} />
        {data && (
          <div role="status" className="flex gap-2 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700 dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-300">
            <CheckCircle2 className="h-4 w-4 shrink-0" />{data.message || 'Email sent.'}
          </div>
        )}
        <button className="btn-primary" disabled={loading}><Send className="h-4 w-4" />Review and send</button>
      </form>
      <ConfirmDialog open={confirm} busy={loading} title="Send this email?" confirmLabel={loading ? 'Sending…' : 'Send email'} onConfirm={send} onCancel={() => setConfirm(false)}>
        <p>To: <b>{f.to}</b></p>
        <p>Subject: <b>{f.subject}</b></p>
        <p className="mt-2">This sends a real email and can't be undone.</p>
      </ConfirmDialog>
    </div>
  )
}
