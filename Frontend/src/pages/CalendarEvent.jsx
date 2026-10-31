import { useEffect, useState } from 'react'
import { CalendarPlus, CheckCircle2, X, Sparkles } from 'lucide-react'
import Field from '../components/Field.jsx'
import ErrorMessage from '../components/ErrorMessage.jsx'
import GmailConnect from '../components/GmailConnect.jsx'
import useRequest from '../hooks/useRequest.js'
import { createCalendarDraft, decideCalendar, getGoogleStatus } from '../api/axios.js'
import { useApp } from '../context/AppContext.jsx'

// The user's own timezone, sent to the backend so "tomorrow at 4pm" is resolved correctly
const browserTimezone = () => {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || undefined
  } catch {
    return undefined
  }
}

export default function CalendarEvent() {
  const { addActivity } = useApp()
  const [calendarReady, setCalendarReady] = useState(null) // null = checking
  const [form, setForm] = useState({ sender: '', subject: '', body: '' })
  const [threadId, setThreadId] = useState(null)
  const [ev, setEv] = useState(null)
  const [tz, setTz] = useState('')
  const [invites, setInvites] = useState(false)
  const [noMeeting, setNoMeeting] = useState(false)
  const [done, setDone] = useState(null) // { link } | 'rejected'

  const drafting = useRequest(createCalendarDraft)
  const deciding = useRequest(decideCalendar)
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })
  const setE = (k) => (e) => setEv({ ...ev, [k]: e.target.value })

  // Check whether Google Calendar is connected before showing the form
  useEffect(() => {
    let alive = true
    getGoogleStatus()
      .then((s) => alive && setCalendarReady(Boolean(s.calendar)))
      // If the status call fails, show the form anyway: the backend still enforces the check
      .catch(() => alive && setCalendarReady(true))
    return () => { alive = false }
  }, [])

  const detect = async (e) => {
    e.preventDefault()
    if (!form.body.trim()) return drafting.fail('Paste the email body first.')
    deciding.reset()
    setNoMeeting(false)
    const res = await drafting.run({
      sender: form.sender.trim() || 'unknown',
      subject: form.subject.trim() || '(no subject)',
      body: form.body,
      timezone: browserTimezone(),
    })
    if (!res) return
    if (!res.has_meeting) return setNoMeeting(true)
    setThreadId(res.thread_id)
    setTz(res.timezone || '')
    setEv({
      title: res.event.title ?? '',
      date: res.event.date ?? '',
      start_time: res.event.start_time ?? '',
      end_time: res.event.end_time ?? '',
      location: res.event.location ?? '',
      attendees: (res.event.attendees ?? []).join(', '),
      description: res.event.description ?? '',
    })
  }

  const approve = async () => {
    if (!ev.date || !ev.start_time) return deciding.fail('Date and start time are required.')
    const res = await deciding.run({
      thread_id: threadId,
      action: 'approve',
      send_invites: invites,
      event: {
        title: ev.title.trim() || 'Meeting',
        date: ev.date,
        start_time: ev.start_time,
        end_time: ev.end_time || null,
        location: ev.location.trim() || null,
        attendees: ev.attendees.split(',').map((a) => a.trim()).filter(Boolean),
        description: ev.description,
      },
    })
    if (res) {
      addActivity('Calendar Event', ev.title, 'Created')
      setDone({ link: res.link })
    }
  }

  const reject = async () => {
    const res = await deciding.run({ thread_id: threadId, action: 'reject' })
    if (res) {
      addActivity('Calendar Event', ev.title, 'Rejected')
      setDone('rejected')
    }
  }

  const startOver = () => {
    setEv(null)
    setThreadId(null)
    setDone(null)
    setInvites(false)
    deciding.reset()
    drafting.reset()
  }

  // ---------- Checking connection ----------
  if (calendarReady === null) {
    return <p className="mx-auto max-w-3xl text-sm text-slate-500">Loading…</p>
  }

  // ---------- Calendar not connected ----------
  if (!calendarReady) {
    return (
      <div className="mx-auto max-w-3xl space-y-4">
        <p className="rounded-lg bg-amber-50 p-3 text-sm text-amber-800 dark:bg-amber-500/10 dark:text-amber-300">
          Connect your Google Calendar once to add meetings found in your emails.
        </p>
        <GmailConnect feature="calendar" />
      </div>
    )
  }

  // ---------- Result ----------
  if (done) {
    const rejected = done === 'rejected'
    return (
      <div className="mx-auto max-w-3xl card space-y-4">
        <div role="status" className="flex gap-2 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700 dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-300">
          <CheckCircle2 className="h-4 w-4 shrink-0" />
          {rejected ? 'Event rejected. Nothing was added.' : 'Event added to Google Calendar.'}
          {/* Only show the link for a created event, not for a rejected one */}
          {!rejected && done.link && (
            <a href={done.link} target="_blank" rel="noreferrer" className="underline">Open</a>
          )}
        </div>
        <button className="btn-primary" onClick={startOver}>Check another email</button>
      </div>
    )
  }

  // ---------- Review ----------
  if (ev) {
    return (
      <div className="mx-auto max-w-3xl space-y-4">
        <p className="rounded-lg bg-amber-50 p-3 text-sm text-amber-800 dark:bg-amber-500/10 dark:text-amber-300">
          Nothing is added to your calendar yet. Check the details, edit if needed, then approve.
          {tz && <span className="block text-xs opacity-80">Times are in {tz}.</span>}
        </p>
        <div className="card space-y-4">
          <Field id="title" label="Title" value={ev.title} onChange={setE('title')} />
          <div className="grid gap-4 sm:grid-cols-3">
            <label className="text-sm">Date
              <input type="date" className="input mt-1 w-full" value={ev.date} onChange={setE('date')} />
            </label>
            <label className="text-sm">Start time
              <input type="time" className="input mt-1 w-full" value={ev.start_time} onChange={setE('start_time')} />
            </label>
            <label className="text-sm">End time (blank = 1 hour)
              <input type="time" className="input mt-1 w-full" value={ev.end_time} onChange={setE('end_time')} />
            </label>
          </div>
          <Field id="location" label="Location or link (optional)" value={ev.location} onChange={setE('location')} />
          <Field id="attendees" label="Attendees (comma separated emails)" value={ev.attendees} onChange={setE('attendees')} />
          <Field id="description" as="textarea" rows={3} label="Description" value={ev.description} onChange={setE('description')} />
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={invites} onChange={(e) => setInvites(e.target.checked)} />
            Also email invites to attendees
          </label>
          <ErrorMessage message={deciding.error} />
          <div className="flex flex-wrap gap-3">
            <button className="btn-primary" onClick={approve} disabled={deciding.loading}>
              <CalendarPlus className="h-4 w-4" />{deciding.loading ? 'Adding…' : 'Approve and add'}
            </button>
            <button className="btn-secondary" onClick={reject} disabled={deciding.loading}>
              <X className="h-4 w-4" />Reject
            </button>
          </div>
        </div>
      </div>
    )
  }

  // ---------- Input ----------
  return (
    <div className="mx-auto max-w-3xl space-y-4">
      {noMeeting && (
        <p className="rounded-lg bg-slate-100 p-3 text-sm text-slate-700 dark:bg-slate-500/10 dark:text-slate-300">
          No meeting with a date or time was found in this email.
        </p>
      )}
      <form onSubmit={detect} className="card space-y-4" noValidate>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field id="sender" label="From (optional)" value={form.sender} onChange={set('sender')} />
          <Field id="subject" label="Subject (optional)" value={form.subject} onChange={set('subject')} />
        </div>
        <Field id="body" as="textarea" rows={10} label="Email text" placeholder="Hi, can we meet tomorrow at 4pm on Google Meet?" value={form.body} onChange={set('body')} />
        <ErrorMessage message={drafting.error} />
        <button className="btn-primary" disabled={drafting.loading}>
          <Sparkles className="h-4 w-4" />{drafting.loading ? 'Detecting…' : 'Detect meeting'}
        </button>
      </form>
    </div>
  )
}