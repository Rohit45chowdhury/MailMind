import { useState } from 'react'
import { Loader2, Mail, ShieldAlert, ShieldCheck } from 'lucide-react'
import Field, { EmptyState } from '../components/Field.jsx'
import ErrorMessage from '../components/ErrorMessage.jsx'
import useRequest from '../hooks/useRequest.js'
import { checkSpam } from '../api/axios.js'
import { useApp } from '../context/AppContext.jsx'
import { pct } from '../utils.js'

export default function SpamDetection() {
  const [f, setF] = useState({ sender: '', subject: '', body: '' })
  const { loading, error, data, run, fail } = useRequest(checkSpam)
  const { addActivity } = useApp()
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })

  const submit = async (e) => {
    e.preventDefault()
    if (!f.sender.trim() || !f.subject.trim() || !f.body.trim()) return fail('Fill in the sender, subject and email body.')
    const res = await run({ sender: f.sender.trim(), subject: f.subject.trim(), body: f.body.trim() })
    if (res) addActivity('Spam Detection', f.sender, res.is_spam ? 'Spam' : 'Not spam')
  }

  const spam = data?.is_spam === true
  return (
    <div className="mx-auto grid max-w-6xl gap-6 lg:grid-cols-2">
      <form onSubmit={submit} className="card space-y-4" noValidate>
        <Field id="sender" label="Sender email" type="email" placeholder="hr@example.com" value={f.sender} onChange={set('sender')} />
        <Field id="subject" label="Subject" placeholder="Interview Invitation" value={f.subject} onChange={set('subject')} />
        <Field id="body" as="textarea" rows={8} label="Email body" placeholder="Paste the email content here…" value={f.body} onChange={set('body')} />
        <button className="btn-primary" disabled={loading}>{loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <ShieldAlert className="h-4 w-4" />}{loading ? 'Checking…' : 'Check spam'}</button>
      </form>
      <section className="card space-y-4" aria-live="polite">
        <h2 className="font-semibold text-slate-900 dark:text-white">Result</h2>
        <ErrorMessage message={error} />
        {!data && !error && !loading && <EmptyState icon={Mail} title="No result yet" text="Enter an email and select Check spam to see the verdict." />}
        {loading && <EmptyState icon={Loader2} title="Analyzing email…" text="This usually takes a few seconds." />}
        {data && (
          <div className={`rounded-xl border p-4 ${spam ? 'border-red-200 bg-red-50 dark:border-red-500/30 dark:bg-red-500/10' : 'border-emerald-200 bg-emerald-50 dark:border-emerald-500/30 dark:bg-emerald-500/10'}`}>
            <div className="flex items-center gap-3">
              {spam ? <ShieldAlert className="h-8 w-8 text-red-600" /> : <ShieldCheck className="h-8 w-8 text-emerald-600" />}
              <div>
                <p className="text-lg font-semibold text-slate-900 dark:text-white">{data.verdict ?? (spam ? 'Spam' : 'Not spam')}</p>
                <p className="text-sm text-slate-600 dark:text-slate-400">is_spam: {String(data.is_spam)} · Confidence {pct(data.confidence)}</p>
              </div>
            </div>
            {data.reason && <p className="mt-3 text-sm text-slate-700 dark:text-slate-300"><span className="font-medium">Reason: </span>{data.reason}</p>}
          </div>
        )}
      </section>
    </div>
  )
}
