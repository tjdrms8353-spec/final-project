import React, { createContext, useContext, useEffect, useState } from 'react'
import { api, getToken, setToken } from './api'

const AuthCtx = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!getToken()) { setLoading(false); return }
    api('/api/auth/me')
      .then(setUser)
      .catch(() => setToken(null))
      .finally(() => setLoading(false))
  }, [])

  const login = async (email, password) => {
    const res = await api('/api/auth/login', { method: 'POST', body: { email, password } })
    setToken(res.token)
    setUser(res.user)
    return res.user
  }

  const logout = async () => {
    try { await api('/api/auth/logout', { method: 'POST' }) } catch {}
    setToken(null)
    setUser(null)
    window.location.href = '/'
  }

  return <AuthCtx.Provider value={{ user, loading, login, logout }}>{children}</AuthCtx.Provider>
}

export function useAuth() { return useContext(AuthCtx) }
