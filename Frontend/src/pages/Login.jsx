import { useEffect, useState } from 'react'
import { Navigate, useLocation, useSearchParams } from 'react-router-dom'
import { Loader2, Mail, ShieldCheck } from 'lucide-react'
import AuthShell from '../components/AuthShell.jsx'
import Field from '../components/Field.jsx'
import ErrorMessage from '../components/ErrorMessage.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import { googleLoginUrl } from '../api/axios.js'

// Backend Google login fail hone par /login?gmail=<reason> pe wapas bhejta hai
const GOOGLE_ERRORS = {
  denied: 'Google permission nahi di gayi. Login ke liye Allow dabana zaroori hai.',
  failed: 'Google login poora nahi hua. Dobara try karo.',
  invalid: 'Login session expire ho gaya. Dobara try karo.',
}

// Backend base URL, derived from the Google login URL (e.g. http://localhost:8000)
const API = googleLoginUrl.replace(/\/google\/login\/?$/, '')

// POST helper: sends cookies, returns JSON, throws Error with a readable message
async function post(path, body) {
  let res
  try {
    res = await fetch(`${API}${path}`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
  } catch {
    throw new Error('Server se connect nahi ho paya. Backend chal raha hai?')
  }
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    const d = data.detail
    // FastAPI sends a string for our errors and a list for validation errors (422)
    throw new Error(typeof d === 'string' ? d : 'Sahi email / OTP daalo aur dobara try karo.')
  }
  return data
}

function GoogleIcon() {
  return (
    <svg viewBox="0 0 48 48" className="h-4 w-4" aria-hidden="true">
      <path fill="#EA4335" d="M24 9.5c3.5 0 6.6 1.2 9.1 3.6l6.8-6.8C35.8 2.4 30.3 0 24 0 14.6 0 6.5 5.4 2.6 13.2l7.9 6.1C12.4 13.5 17.7 9.5 24 9.5z" />
      <path fill="#4285F4" d="M46.5 24.5c0-1.6-.1-3.1-.4-4.5H24v9h12.7c-.6 3-2.3 5.5-4.8 7.2l7.5 5.8c4.4-4.1 7.1-10.1 7.1-17.5z" />
      <path fill="#FBBC05" d="M10.5 28.7a14.5 14.5 0 0 1 0-9.4l-7.9-6.1a24 24 0 0 0 0 21.6l7.9-6.1z" />
      <path fill="#34A853" d="M24 48c6.5 0 11.9-2.1 15.9-5.8l-7.5-5.8c-2.1 1.4-4.9 2.3-8.4 2.3-6.3 0-11.6-4-13.5-9.8l-7.9 6.1C6.5 42.6 14.6 48 24 48z" />
    </svg>
  )
}

export default function Login() {
  const { user } = useAuth()
  const location = useLocation()
  const [params] = useSearchParams()

  const [step, setStep] = useState('email') // 'email' | 'otp'
  const [email, setEmail] = useState('')
  const [otp, setOtp] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [cooldown, setCooldown] = useState(0) // seconds until "Resend" is enabled

  // Countdown for the resend button
  useEffect(() => {
    if (cooldown <= 0) return
    const t = setTimeout(() => setCooldown((c) => c - 1), 1000)
    return () => clearTimeout(t)
  }, [cooldown])

  if (user) return <Navigate to={location.state?.from || '/'} replace />

  const googleError = GOOGLE_ERRORS[params.get('gmail')]

  const sendOtp = async (e) => {
    e?.preventDefault()
    const clean = email.trim().toLowerCase()
    if (!/^\S+@\S+\.\S+$/.test(clean)) return setError('Sahi email daalo.')
    setLoading(true); setError('')
    try {
      const data = await post('/auth/send-otp', { email: clean })
      setEmail(clean)
      setOtp('')
      setStep('otp')
      setCooldown(data.resend_in || 60)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const verifyOtp = async (e) => {
    e.preventDefault()
    if (otp.length !== 6) return setError('6 digit ka OTP daalo.')
    setLoading(true); setError('')
    try {
      await post('/auth/verify-otp', { email, otp })
      // Cookie is set. Full reload so AuthContext picks up the signed-in user.
      window.location.assign(location.state?.from || '/')
    } catch (err) {
      setError(err.message)
      setLoading(false)
    }
  }

  const changeEmail = () => {
    setStep('email'); setOtp(''); setError(''); setCooldown(0)
  }

  return (
    <AuthShell
      title="Sign in"
      subtitle="Enter your email and we'll send you a code. New here? We'll create your account."
      footer={<>No password needed. We only use your email to sign you in.</>}>
      <div className="space-y-4">
        <ErrorMessage message={googleError} />

        {/* Plain link: poora browser Google pe redirect hota hai, axios call nahi */}
        <a href={googleLoginUrl} className="btn-secondary flex w-full items-center justify-center gap-2">
          <GoogleIcon />Continue with Google
        </a>

        <div className="flex items-center gap-3 text-xs text-slate-400">
          <span className="h-px flex-1 bg-slate-200 dark:bg-slate-800" />
          or continue with email
          <span className="h-px flex-1 bg-slate-200 dark:bg-slate-800" />
        </div>

        {step === 'email' ? (
          <form onSubmit={sendOtp} className="space-y-4" noValidate>
            <Field id="email" label="Email" type="email" autoComplete="email" placeholder="you@example.com"
              value={email} onChange={(e) => setEmail(e.target.value)} />
            <ErrorMessage message={error} />
            <button className="btn-primary w-full" disabled={loading}>
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Mail className="h-4 w-4" />}
              {loading ? 'Sending…' : 'Get OTP'}
            </button>
          </form>
        ) : (
          <form onSubmit={verifyOtp} className="space-y-4" noValidate>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              OTP Sent: <span className="font-medium text-slate-900 dark:text-slate-100">{email}</span>
            </p>
            {/* Digits only, max 6 */}
            <Field id="otp" label="6-digit OTP" autoComplete="one-time-code" inputMode="numeric" maxLength={6} placeholder="123456"
              value={otp} onChange={(e) => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))} />
            <ErrorMessage message={error} />
            <button className="btn-primary w-full" disabled={loading}>
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <ShieldCheck className="h-4 w-4" />}
              {loading ? 'Verifying…' : 'Verify & continue'}
            </button>
            <div className="flex items-center justify-between text-sm">
              <button type="button" onClick={changeEmail} className="font-medium text-indigo-600 hover:underline">
                Change email
              </button>
              <button type="button" onClick={sendOtp} disabled={loading || cooldown > 0}
                className="font-medium text-indigo-600 hover:underline disabled:cursor-not-allowed disabled:text-slate-400 disabled:no-underline">
                {cooldown > 0 ? `Resend OTP in ${cooldown}s` : 'Resend OTP'}
              </button>
            </div>
          </form>
        )}
      </div>
    </AuthShell>
  )
}