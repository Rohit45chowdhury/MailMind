export default function SplashScreen() {
  return (
    <div role="status" aria-live="polite" className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-navy-900 px-6 text-center">
      <div className="animate-bob rounded-3xl bg-white p-4 shadow-2xl shadow-indigo-500/20 motion-reduce:animate-none">
        <img src="/logo.jpg" alt="" className="h-24 w-24 rounded-2xl object-cover" />
      </div>
      <h1 className="mt-8 text-2xl font-semibold text-white">MailMind AI</h1>
      <p className="mt-1 text-sm text-slate-400">Your Inbox, Intelligently Managed.</p>
      <div className="mt-8 h-1.5 w-48 overflow-hidden rounded-full bg-white/10">
        <div className="h-full w-1/3 animate-load rounded-full bg-indigo-400 motion-reduce:animate-none" />
      </div>
      <span className="sr-only">Loading MailMind AI</span>
    </div>
  )
}
