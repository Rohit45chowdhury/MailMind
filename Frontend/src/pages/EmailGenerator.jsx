import { useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { Loader2, PenLine, Send, Trash2 } from 'lucide-react'
import Field, { EmptyState } from '../components/Field.jsx'
import ErrorMessage from '../components/ErrorMessage.jsx'
import CopyButton from '../components/CopyButton.jsx'
import useRequest from '../hooks/useRequest.js'
import { generateEmail } from '../api/axios.js'
import { useApp } from '../context/AppContext.jsx'

const tones = ['formal', 'professional', 'friendly', 'casual', 'persuasive', 'apologetic', 'urgent']
const lengths = ['short', 'medium', 'long']
const emojis = ['none', 'minimal', 'moderate', 'expressive']
const cap = (s) => s[0].toUpperCase() + s.slice(1)

export default function EmailGenerator() {
  const { state } = useLocation()
  const navigate = useNavigate()
  const { addActivity } = useApp()
  const [f, setF] = useState({ purpose: state?.purpose || '', recipient: '', sender_name: '', tone: 'professional', length: 'medium', emoji: 'none', language: 'English' })
  const [out, setOut] = useState({ subject: '', body: '' })
  const { loading, error, data, run, fail, reset } = useRequest(generateEmail)
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })

  useEffect(() => { if (data) setOut({ subject: data.subject ?? '', body: data.body ?? '' }) }, [data])

  const submit = async (e) => {
    e.preventDefault()
    if (!f.purpose.trim() || !f.recipient.trim() || !f.sender_name.trim()) return fail('Fill in the purpose, recipient and your name.')
    const res = await run({ ...f, language: f.language.trim() || 'English' })
    if (res) addActivity('Email Generator', f.purpose.slice(0, 50), 'Generated')
  }
  const clear = () => { reset(); setOut({ subject: '', body: '' }) }

  return (
    <div className="mx-auto grid max-w-6xl gap-6 lg:grid-cols-2">
      <form onSubmit={submit} className="card space-y-4" noValidate>
        <Field id="purpose" as="textarea" rows={3} label="Purpose or topic" placeholder="Request an extension for my assignment" value={f.purpose} onChange={set('purpose')} />
        <div className="grid gap-4 sm:grid-cols-2">
          <Field id="recipient" label="Recipient" placeholder="Professor" value={f.recipient} onChange={set('recipient')} />
          <Field id="sender_name" label="Your name" placeholder="Student" value={f.sender_name} onChange={set('sender_name')} />
          <Field id="tone" as="select" label="Tone" value={f.tone} onChange={set('tone')}>{tones.map((t) => <option key={t} value={t}>{cap(t)}</option>)}</Field>
          <Field id="length" as="select" label="Length" value={f.length} onChange={set('length')}>{lengths.map((t) => <option key={t} value={t}>{cap(t)}</option>)}</Field>
          <Field id="emoji" as="select" label="Emoji" value={f.emoji} onChange={set('emoji')}>{emojis.map((t) => <option key={t} value={t}>{cap(t)}</option>)}</Field>
          <Field id="language" label="Language" value={f.language} onChange={set('language')} />
        </div>
        <button className="btn-primary" disabled={loading}>{loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <PenLine className="h-4 w-4" />}{loading ? 'Generating…' : 'Generate email'}</button>
      </form>
      <section className="card space-y-4" aria-live="polite">
        <h2 className="font-semibold text-slate-900 dark:text-white">Generated email</h2>
        <ErrorMessage message={error} />
        {!data && !error && !loading && <EmptyState icon={PenLine} title="No email yet" text="Describe what you need and select Generate email. You can edit the result." />}
        {loading && <EmptyState icon={Loader2} title="Writing your email…" text="This usually takes a few seconds." />}
        {data && (
          <>
            <Field id="out-subject" label="Subject" value={out.subject} onChange={(e) => setOut({ ...out, subject: e.target.value })} />
            <Field id="out-body" as="textarea" rows={12} label="Body" value={out.body} onChange={(e) => setOut({ ...out, body: e.target.value })} />
            <div className="flex flex-wrap gap-2">
              <CopyButton text={out.subject} label="Copy subject" />
              <CopyButton text={out.body} label="Copy body" />
              <button type="button" className="btn-ghost" onClick={() => navigate('/send', { state: out })}><Send className="h-4 w-4" />Use in Send Email</button>
              <button type="button" className="btn-ghost" onClick={clear}><Trash2 className="h-4 w-4" />Clear</button>
            </div>
          </>
        )}
      </section>
    </div>
  )
}
