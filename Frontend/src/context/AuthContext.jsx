import { createContext, useContext, useEffect, useState } from 'react'
import { getMe, loginUser, logoutUser, registerUser } from '../api/axios.js'

const Ctx = createContext(null)
export const useAuth = () => useContext(Ctx)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true) // true while we check /auth/me

  useEffect(() => {
    let off = false
    getMe().then((u) => !off && setUser(u)).catch(() => {}).finally(() => !off && setLoading(false))
    const expired = () => setUser(null)
    window.addEventListener('mm-unauthorized', expired)
    return () => { off = true; window.removeEventListener('mm-unauthorized', expired) }
  }, [])

  const login = async (payload) => setUser(await loginUser(payload))
  const register = async (payload) => setUser(await registerUser(payload))
  const logout = async () => {
    try { await logoutUser() } finally { setUser(null) }
  }

  return <Ctx.Provider value={{ user, loading, login, register, logout }}>{children}</Ctx.Provider>
}
