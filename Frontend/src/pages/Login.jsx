import { useState } from 'react'
import { Link, Navigate, useLocation } from 'react-router-dom'
import { Loader2, LogIn } from 'lucide-react'
import AuthShell from '../components/AuthShell.jsx'
import Field from '../components/Field.jsx'
import PasswordField from '../components/PasswordField.jsx'
import ErrorMessage from '../components/ErrorMessage.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import { getErrorMessage } from '../api/axios.js'

export default function Login() {
  const { user, login } = useAuth()
  const location = useLocation()
  const [f, setF] = useState({ email: '', password: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })

  if (user) return <Navigate to={location.state?.from || '/'} replace />

  const submit = async (e) => {
    e.preventDefault()
    if (!f.email.trim() || !f.password) return setError('Enter your email and 4-digit PIN.')
    setLoading(true); setError('')
    try {
      await login({ email: f.email.trim(), password: f.password })
    } catch (err) {
      setError(getErrorMessage(err))
      setLoading(false)
    }
  }

  return (
    <AuthShell title="Sign in" subtitle="Welcome back. Sign in to use your email tools."
      footer={<>New to MailMind AI? <Link to="/register" className="font-medium text-indigo-600 hover:underline">Create an account</Link></>}>
      <form onSubmit={submit} className="space-y-4" noValidate>
        <Field id="email" label="Email" type="email" autoComplete="email" placeholder="you@example.com" value={f.email} onChange={set('email')} />
        <PasswordField id="password" label="4-digit PIN" autoComplete="current-password" inputMode="numeric" maxLength={4} placeholder="4 digits"
          value={f.password} onChange={(e) => setF({ ...f, password: e.target.value.replace(/\D/g, '').slice(0, 4) })} />
        <ErrorMessage message={error} />
        <button className="btn-primary w-full" disabled={loading}>
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <LogIn className="h-4 w-4" />}{loading ? 'Signing in…' : 'Sign in'}
        </button>
      </form>
    </AuthShell>
  )
}