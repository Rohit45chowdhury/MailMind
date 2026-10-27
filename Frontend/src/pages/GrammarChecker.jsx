import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { CheckCircle2, Loader2, PenLine, SpellCheck } from 'lucide-react'
import Field, { EmptyState, Toggle } from '../components/Field.jsx'
import ErrorMessage from '../components/ErrorMessage.jsx'
import CopyButton from '../components/CopyButton.jsx'
import useRequest from '../hooks/useRequest.js'
import { checkGrammar } from '../api/axios.js'
import { useApp } from '../context/AppContext.jsx'

export default function GrammarChecker() {
  const [text, setText] = useState('')
  const [language, setLanguage] = useState('English')
  const [strict, setStrict] = useState(false)
  const [corrected, setCorrected] = useState('')
  const { loading, error, data, run, fail } = useRequest(checkGrammar)
  const { addActivity } = useApp()
  const navigate = useNavigate()

  useEffect(() => { if (data) setCorrected(data.corrected_text ?? data.corrected ?? '') }, [data])

  const submit = async (e) => {
    e.preventDefault()
    if (!text.trim()) return fail('Enter some text to check.')
    const res = await run({ text, language: language.trim() || 'English', strict })
    if (res) addActivity('Grammar Check', text.slice(0, 40), res.has_errors ? `${res.issue_count ?? ''} issues`.trim() : 'No errors')
  }

  const issues = Array.isArray(data?.issues) ? data.issues : []
  return (
    <div className="mx-auto grid max-w-6xl gap-6 lg:grid-cols-2">
      <form onSubmit={submit} className="card space-y-4" noValidate>
        <Field id="text" as="textarea" rows={12} label="Your text" placeholder="dear sir, i has completed the work." value={text} onChange={(e) => setText(e.target.value)} />
        <div className="flex flex-wrap items-end gap-4">
          
          <Field
            id="lang"
            as="select"
            label="Language"
            className="w-40"
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
          >
            <option value="English">English</option>
            <option value="Hindi">Hindi</option>
          </Field>

          <Toggle id="strict" checked={strict} onChange={setStrict} label="Strict mode" />
        </div>
        <button className="btn-primary" disabled={loading}>{loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <SpellCheck className="h-4 w-4" />}{loading ? 'Checking…' : 'Check grammar'}</button>
      </form>
      <section className="card space-y-4" aria-live="polite">
        <h2 className="font-semibold text-slate-900 dark:text-white">Result</h2>
        <ErrorMessage message={error} />
        {!data && !error && !loading && <EmptyState icon={SpellCheck} title="No result yet" text="Enter some text and select Check grammar." />}
        {loading && <EmptyState icon={Loader2} title="Checking your text…" text="This usually takes a few seconds." />}
        {data && (
          <>
            <div>
              <p className="label">Original</p>
              <p className="rounded-lg bg-slate-50 p-3 text-sm text-slate-600 dark:bg-slate-950 dark:text-slate-400">{data.original_text ?? data.original ?? text}</p>
            </div>
            <div className={`flex items-center gap-2 text-sm font-medium ${data.has_errors ? 'text-amber-600' : 'text-emerald-600'}`}>
              <CheckCircle2 className="h-4 w-4" />{data.has_errors ? `Errors found: ${data.issue_count ?? issues.length}` : 'No errors found'}
            </div>
            <Field id="corrected" as="textarea" rows={5} label="Corrected text (editable)" value={corrected} onChange={(e) => setCorrected(e.target.value)} />
            <div className="flex flex-wrap gap-2">
              <CopyButton text={corrected} label="Copy corrected text" />
              <button type="button" className="btn-ghost" disabled={!corrected} onClick={() => navigate('/generate', { state: { purpose: corrected } })}><PenLine className="h-4 w-4" />Use in Email Generator</button>
            </div>
            {issues.length > 0 && (
              <ul className="space-y-2">
                {issues.map((it, i) => (
                  <li key={i} className="rounded-lg border border-slate-200 p-3 text-sm dark:border-slate-800">
                    <p><span className="text-red-600 line-through">{it.original}</span> → <span className="font-medium text-emerald-600">{it.correction}</span>
                      {it.type && <span className="ml-2 rounded-full bg-slate-100 px-2 py-0.5 text-xs dark:bg-slate-800">{it.type}</span>}</p>
                    {it.explanation && <p className="mt-1 text-slate-500 dark:text-slate-400">{it.explanation}</p>}
                  </li>
                ))}
              </ul>
            )}
          </>
        )}
      </section>
    </div>
  )
}
