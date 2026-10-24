import { lazy, Suspense, useEffect, useState } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import DashboardLayout from './layouts/DashboardLayout.jsx'
import SplashScreen from './components/SplashScreen.jsx'
import LoadingSpinner from './components/LoadingSpinner.jsx'
import ProtectedRoute from './components/ProtectedRoute.jsx'
import DraftApproval from './pages/DraftApproval.jsx'
import CalendarEvent from './pages/CalendarEvent.jsx'

const Dashboard = lazy(() => import('./pages/Dashboard.jsx'))
const SpamDetection = lazy(() => import('./pages/SpamDetection.jsx'))
const Summarizer = lazy(() => import('./pages/Summarizer.jsx'))
const EmailGenerator = lazy(() => import('./pages/EmailGenerator.jsx'))
const GrammarChecker = lazy(() => import('./pages/GrammarChecker.jsx'))

const Settings = lazy(() => import('./pages/Settings.jsx'))
const Login = lazy(() => import('./pages/Login.jsx'))
const Register = lazy(() => import('./pages/Register.jsx'))

export default function App() {
  const [booting, setBooting] = useState(true)
  useEffect(() => {
    const t = setTimeout(() => setBooting(false), 1800) // loading page shown on first load
    return () => clearTimeout(t)
  }, [])
  if (booting) return <SplashScreen />

  return (
    <Suspense fallback={<LoadingSpinner label="Loading page…" className="min-h-screen" />}>
      <Routes>
        <Route path="login" element={<Login />} />
        <Route path="register" element={<Register />} />
        <Route element={<ProtectedRoute />}>
        <Route element={<DashboardLayout />}>
          <Route index element={<Dashboard />} />
          <Route path="spam" element={<SpamDetection />} />
          <Route path="summarize" element={<Summarizer />} />
          <Route path="generate" element={<EmailGenerator />} />
          <Route path="grammar" element={<GrammarChecker />} />
          
          
          <Route path="draft" element={<DraftApproval />} />
          <Route path="calendar" element={<CalendarEvent />} />
          <Route path="settings" element={<Settings />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
        </Route>
      </Routes>
    </Suspense>
  )
}
