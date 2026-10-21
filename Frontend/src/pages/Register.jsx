import { useState } from 'react'
import { Link, Navigate } from 'react-router-dom'
import { Loader2, UserPlus } from 'lucide-react'
import AuthShell from '../components/AuthShell.jsx'
import Field from '../components/Field.jsx'
import PasswordField from '../components/PasswordField.jsx'
import ErrorMessage from '../components/ErrorMessage.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import { getErrorMessage } from '../api/axios.js'

export default function Register() {
  const { user, register } = useAuth()
  const [f, setF] = useState({ name: '', email: '', password: '', confirm: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })
  const pin = (k) => (e) => setF({ ...f, [k]: e.target.value.replace(/\D/g, '').slice(0, 4) }) // digits only, max 4

  if (user) return <Navigate to="/" replace />

  const submit = async (e) => {
    e.preventDefault()
    if (f.name.trim().length < 2) return setError('Enter your name (at least 2 characters).')
    if (!/^\S+@\S+\.\S+$/.test(f.email.trim())) return setError('Enter a valid email address.')
    if (!/^\d{4}$/.test(f.password)) return setError('PIN must be exactly 4 digits.')
    if (f.password !== f.confirm) return setError('PINs do not match.')
    setLoading(true); setError('')
    try {
      await register({ name: f.name.trim(), email: f.email.trim(), password: f.password })
    } catch (err) {
      setError(getErrorMessage(err))
      setLoading(false)
    }
  }

  return (
    <AuthShell title="Create your account" subtitle="Start managing your inbox with AI."
      footer={<>Already have an account? <Link to="/login" className="font-medium text-indigo-600 hover:underline">Sign in</Link></>}>
      <form onSubmit={submit} className="space-y-4" noValidate>
        <Field id="name" label="Full name" autoComplete="name" placeholder="Rohit Kumar" value={f.name} onChange={set('name')} />
        <Field id="email" label="Email" type="email" autoComplete="email" placeholder="you@example.com" value={f.email} onChange={set('email')} />
        <PasswordField id="password" label="4-digit PIN" autoComplete="new-password" inputMode="numeric" maxLength={4} placeholder="4 digits" value={f.password} onChange={pin('password')} />
        <PasswordField id="confirm" label="Confirm PIN" autoComplete="new-password" inputMode="numeric" maxLength={4} placeholder="Repeat the 4 digits" value={f.confirm} onChange={pin('confirm')} />
        <ErrorMessage message={error} />
        <button className="btn-primary w-full" disabled={loading}>
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <UserPlus className="h-4 w-4" />}{loading ? 'Creating account…' : 'Create account'}
        </button>
      </form>
    </AuthShell>
  )
}