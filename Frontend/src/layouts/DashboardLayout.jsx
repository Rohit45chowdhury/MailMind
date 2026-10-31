import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import Sidebar from '../components/Sidebar.jsx'
import Header from '../components/Header.jsx'

export default function DashboardLayout() {
  const [open, setOpen] = useState(false)
  return (
    <div className="flex min-h-screen">
      <Sidebar open={open} onClose={() => setOpen(false)} />
      <div className="flex min-w-0 flex-1 flex-col">
        <Header onMenu={() => setOpen(true)} />
        <main className="flex-1 p-4 sm:p-6"><Outlet /></main>
        <footer className="border-t border-slate-200 px-6 py-3 text-xs text-slate-500 dark:border-slate-800">MailMind AI v1.0.0</footer>
      </div>
    </div>
  )
}
