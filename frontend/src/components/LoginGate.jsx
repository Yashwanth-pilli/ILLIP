import React, { useState, useEffect } from 'react'
import { getToken, setToken, clearToken } from '../auth-client.js'

// Gates the app behind the local password — but only when the backend says
// login is enabled. Default (no password set) renders children immediately.
export default function LoginGate({ children }) {
  const [phase, setPhase] = useState('loading') // loading | open | login
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const check = async () => {
    try {
      const r = await fetch('/api/auth/status', {
        headers: getToken() ? { Authorization: `Bearer ${getToken()}` } : {},
      })
      const d = await r.json()
      if (!d.enabled || d.authenticated) setPhase('open')
      else setPhase('login')
    } catch {
      setPhase('open') // backend unreachable → don't hard-block the shell
    }
  }
  useEffect(() => { check() }, [])

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true); setError('')
    try {
      const r = await fetch('/api/auth/login', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password }),
      })
      if (!r.ok) { setError('Wrong password.'); setBusy(false); return }
      const d = await r.json()
      setToken(d.token)
      setPassword('')
      setPhase('open')
    } catch {
      setError('Could not reach ILLIP.')
    }
    setBusy(false)
  }

  if (phase === 'loading') return null
  if (phase === 'open') return children

  return (
    <div className="login-gate">
      <form className="login-card" onSubmit={submit}>
        <video className="login-logo" src="/illip-logo.mp4" poster="/illip-logo.png" autoPlay loop muted playsInline />
        <h1 className="login-title">ILLIP</h1>
        <p className="login-sub">Private · Local · Yours</p>
        <input
          className="login-input"
          type="password"
          placeholder="Password"
          value={password}
          autoFocus
          onChange={e => setPassword(e.target.value)}
        />
        {error && <div className="login-error">{error}</div>}
        <button className="login-btn" type="submit" disabled={busy || !password}>
          {busy ? 'Checking…' : 'Unlock'}
        </button>
      </form>
    </div>
  )
}

// Small helper exported for a settings/header control to enable or change login.
export async function setLoginPassword(newPassword, currentPassword) {
  const r = await fetch('/api/auth/setup', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ password: newPassword, current_password: currentPassword || null }),
  })
  if (!r.ok) { const d = await r.json().catch(() => ({})); throw new Error(d.detail || 'Failed') }
  const d = await r.json()
  if (d.token) setToken(d.token)
  return d
}

export function logoutLocal() {
  const t = getToken()
  clearToken()
  fetch('/api/auth/logout', { method: 'POST', headers: t ? { Authorization: `Bearer ${t}` } : {} }).catch(() => {})
  location.reload()
}
