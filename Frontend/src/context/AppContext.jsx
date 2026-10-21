import { createContext, useCallback, useContext, useEffect, useState } from 'react'

const Ctx = createContext(null)
export const useApp = () => useContext(Ctx)

export function AppProvider({ children }) {
  const [dark, setDark] = useState(() => {
    try { return localStorage.getItem('mm-theme') === 'dark' } catch { return false }
  })
  // Real results from this browser session only. Not persisted: there is no history endpoint.
  const [activity, setActivity] = useState([])

  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark)
    try { localStorage.setItem('mm-theme', dark ? 'dark' : 'light') } catch { /* storage unavailable */ }
  }, [dark])

  const addActivity = useCallback((tool, detail, status) => {
    setActivity((a) => [{ id: Date.now() + Math.random(), tool, detail, status, at: new Date() }, ...a].slice(0, 8))
  }, [])

  return <Ctx.Provider value={{ dark, toggleTheme: () => setDark((d) => !d), activity, addActivity }}>{children}</Ctx.Provider>
}
