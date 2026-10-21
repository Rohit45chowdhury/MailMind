import { useState } from 'react'
import { FileText, Loader2, ShieldAlert } from 'lucide-react'
import Field, { EmptyState } from '../components/Field.jsx'
import ErrorMessage from '../components/ErrorMessage.jsx'
import CopyButton from '../components/CopyButton.jsx'
import useRequest from '../hooks/useRequest.js'
import { summarizeEmail } from '../api/axios.js'
import { useApp } from '../context/AppContext.jsx'

export default function Summarizer() {
  const [f, setF] = useState({ sender: '', subject: '', body: '' })
  const { loading, error, data, run, fail } = useRequest(summarizeEmail)
  const { addActivity } = useApp()
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })

  const submit = async (e) => {
    e.preventDefault()
    if (!f.sender.trim() || !f.subject.trim() || !f.body.trim()) return fail('Fill in the sender, subject and email body.')
    const res = await run({ sender: f.sender.trim(), subject: f.subject.trim(), body: f.body.trim() })
    if (res) addActivity('Summarizer', f.subject, res.summary ? 'Summary ready' : 'Flagged as spam')
  }

  const reason = data?.spam_reason ?? data?.reason
  return (
    <div className="mx-auto grid max-w-6xl gap-6 lg:grid-cols-2">
      <form onSubmit={submit} className="card space-y-4" noValidate>
        <Field id="sender" label="Sender email" type="email" placeholder="manager@example.com" value={f.sender} onChange={set('sender')} />
        <Field id="subject" label="Subject" placeholder="Project update" value={f.subject} onChange={set('subject')} />
        <Field id="body" as="textarea" rows={9} label="Email body" placeholder="Paste the email content here…" value={f.body} onChange={set('body')} />
        <button className="btn-primary" disabled={loading}>{loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileText className="h-4 w-4" />}{loading ? 'Summarizing…' : 'Summarize email'}</button>
      </form>
      <section className="card space-y-4" aria-live="polite">
        <h2 className="font-semibold text-slate-900 dark:text-white">Summary</h2>
        <ErrorMessage message={error} />
        {!data && !error && !loading && <EmptyState icon={FileText} title="No summary yet" text="Paste an email and select Summarize email." />}
        {loading && <EmptyState icon={Loader2} title="Reading the email…" text="This usually takes a few seconds." />}
        {data && (
          <>
            {data.summary ? (
              <div className="rounded-xl border border-indigo-100 bg-indigo-50 p-4 text-sm leading-relaxed text-slate-800 dark:border-indigo-500/20 dark:bg-indigo-500/10 dark:text-slate-200">{data.summary}</div>
            ) : (
              <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-300">
                No summary was created{data.is_spam ? ' because this email was flagged as spam.' : '.'}
              </div>
            )}
            <div className="flex flex-wrap items-center gap-3 text-sm">
              <span className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 font-medium ${data.is_spam ? 'bg-red-100 text-red-700' : 'bg-emerald-100 text-emerald-700'}`}>
                <ShieldAlert className="h-4 w-4" />{data.is_spam ? 'Spam' : 'Not spam'}
              </span>
              {data.summary && <CopyButton text={data.summary} label="Copy summary" />}
            </div>
            {reason && <p className="text-sm text-slate-700 dark:text-slate-300"><span className="font-medium">Spam reason: </span>{reason}</p>}
          </>
        )}
      </section>
    </div>
  )
}
