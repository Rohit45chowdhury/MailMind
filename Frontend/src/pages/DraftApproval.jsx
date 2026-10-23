import { useState } from 'react'
import { CheckCircle2, Send, X, Sparkles } from 'lucide-react'
import Field from '../components/Field.jsx'
import ErrorMessage from '../components/ErrorMessage.jsx'
import useRequest from '../hooks/useRequest.js'
import { createDraft, decideDraft } from '../api/axios.js'
import { useApp } from '../context/AppContext.jsx'

const TONES = ['formal', 'professional', 'friendly', 'casual', 'persuasive', 'apologetic', 'urgent']
const LENGTHS = ['short', 'medium', 'long']

export default function DraftApproval() {
  const { addActivity } = useApp()
  const [form, setForm] = useState({
    purpose: '', to: '', recipient: '', tone: 'professional', length: 'short', cc: '', bcc: '',
  })
  const [draft, setDraft] = useState(null)      // { thread_id, to, subject, body } (original)
  const [edit, setEdit] = useState({ subject: '', body: '' })
  const [done, setDone] = useState(null)        // 'sent' | 'rejected'

  const drafting = useRequest(createDraft)
  const deciding = useRequest(decideDraft)
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  const makeDraft = async (e) => {
    e.preventDefault()
    if (!form.purpose.trim()) return drafting.fail('Write what the email is about.')
    if (!form.to.includes('@')) return drafting.fail('Enter a valid recipient email address.')
    deciding.reset()
    const res = await drafting.run({
      ...form,
      cc: form.cc.trim() || null,
      bcc: form.bcc.trim() || null,
    })
    if (res) {
      setDraft(res)
      setEdit({ subject: res.subject, body: res.body })
      setDone(null)
    }
  }

  const changed = draft && (edit.subject !== draft.subject || edit.body !== draft.body)

  const approve = async () => {
    const res = await deciding.run(
      changed
        ? { thread_id: draft.thread_id, action: 'edit', subject: edit.subject, body: edit.body }
        : { thread_id: draft.thread_id, action: 'approve' }
    )
    if (res) {
      addActivity('Approved Send', draft.to, 'Sent')
      setDone('sent')
    }
  }

  const reject = async () => {
    const res = await deciding.run({ thread_id: draft.thread_id, action: 'reject' })
    if (res) {
      addActivity('Draft', draft.to, 'Rejected')
      setDone('rejected')
    }
  }

  const startOver = () => {
    setDraft(null)
    setDone(null)
    deciding.reset()
    drafting.reset()
  }

  // ---------- Result screen ----------
  if (done) {
    return (
      <div className="mx-auto max-w-3xl card space-y-4">
        <div role="status" className="flex gap-2 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700 dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-300">
          <CheckCircle2 className="h-4 w-4 shrink-0" />
          {done === 'sent' ? `Email sent to ${draft.to}.` : 'Draft rejected. Nothing was sent.'}
        </div>
        <button className="btn-primary" onClick={startOver}>Write another</button>
      </div>
    )
  }

  // ---------- Review screen ----------
  if (draft) {
    return (
      <div className="mx-auto max-w-3xl space-y-4">
        <p className="rounded-lg bg-amber-50 p-3 text-sm text-amber-800 dark:bg-amber-500/10 dark:text-amber-300">
          Nothing has been sent yet. Review or edit the draft, then approve.
        </p>
        <div className="card space-y-4">
          <p className="text-sm">To: <b>{draft.to}</b></p>
          <Field id="subject" label="Subject" value={edit.subject} onChange={(e) => setEdit({ ...edit, subject: e.target.value })} />
          <Field id="body" as="textarea" rows={12} label="Email body" value={edit.body} onChange={(e) => setEdit({ ...edit, body: e.target.value })} />
          <ErrorMessage message={deciding.error} />
          <div className="flex flex-wrap gap-3">
            <button className="btn-primary" onClick={approve} disabled={deciding.loading || !edit.subject.trim() || !edit.body.trim()}>
              <Send className="h-4 w-4" />
              {deciding.loading ? 'Sending…' : changed ? 'Approve edited and send' : 'Approve and send'}
            </button>
            <button className="btn-secondary" onClick={reject} disabled={deciding.loading}>
              <X className="h-4 w-4" />Reject
            </button>
          </div>
        </div>
      </div>
    )
  }

  // ---------- Form screen ----------
  return (
    <div className="mx-auto max-w-3xl">
      <form onSubmit={makeDraft} className="card space-y-4" noValidate>
        <Field id="purpose" as="textarea" rows={4} label="What should the email say?" placeholder="Request 2 days leave next week for a family function" value={form.purpose} onChange={set('purpose')} />
        <div className="grid gap-4 sm:grid-cols-2">
          <Field id="to" label="To (email)" type="email" placeholder="recipient@example.com" value={form.to} onChange={set('to')} />
          <Field id="recipient" label="Recipient name (optional)" placeholder="Amit" value={form.recipient} onChange={set('recipient')} />
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field id="cc" label="CC (optional)" value={form.cc} onChange={set('cc')} />
          <Field id="bcc" label="BCC (optional)" value={form.bcc} onChange={set('bcc')} />
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="text-sm">Tone
            <select className="input mt-1 w-full" value={form.tone} onChange={set('tone')}>
              {TONES.map((t) => <option key={t}>{t}</option>)}
            </select>
          </label>
          <label className="text-sm">Length
            <select className="input mt-1 w-full" value={form.length} onChange={set('length')}>
              {LENGTHS.map((t) => <option key={t}>{t}</option>)}
            </select>
          </label>
        </div>
        <ErrorMessage message={drafting.error} />
        <button className="btn-primary" disabled={drafting.loading}>
          <Sparkles className="h-4 w-4" />{drafting.loading ? 'Drafting…' : 'Generate draft'}
        </button>
      </form>
    </div>
  )
}