import React, { useState, useEffect } from 'react'
import { api } from '../api.js'

// When RAM is full, ILLIP stops guessing and OFFERS to free memory: it lists the
// heaviest open apps and closes the one you pick (with your click = permission).
// System / ILLIP / Ollama processes are filtered out by the backend.
export default function RamHelper({ hwLive }) {
  const ram = hwLive?.ram_percent || 0
  const tight = ram >= 88 || hwLive?.pressure === 'critical'
  const [open, setOpen] = useState(false)
  const [hogs, setHogs] = useState([])
  const [busy, setBusy] = useState('')
  const [msg, setMsg] = useState('')

  // Auto-collapse when RAM recovers.
  useEffect(() => { if (!tight) { setOpen(false); setMsg('') } }, [tight])

  if (!tight) return null

  const load = async () => {
    setOpen(true); setMsg('')
    try { const d = await api.ramHogs(6); setHogs(d.hogs || []) }
    catch { setMsg('Could not read apps.') }
  }

  const close = async (name) => {
    setBusy(name)
    try {
      const d = await api.closeApp(name)
      setMsg(`Closed ${name} — freed ~${d.freed_gb} GB.`)
      setHogs(h => h.filter(x => x.name !== name))
    } catch (e) { setMsg(`Couldn't close ${name}: ${e.message}`) }
    setBusy('')
  }

  return (
    <div className="ram-helper">
      <div className="ram-helper-head">
        <span>⚠️ RAM {ram.toFixed(0)}% full — ILLIP will be slow. Want me to free memory?</span>
        {!open
          ? <button className="ram-btn" onClick={load}>Show open apps</button>
          : <button className="ram-btn ghost" onClick={() => setOpen(false)}>Hide</button>}
      </div>
      {open && (
        <div className="ram-list">
          {hogs.length === 0 && <div className="ram-muted">No closeable apps found (or already light).</div>}
          {hogs.map(h => (
            <div key={h.name} className="ram-row">
              <span className="ram-name">{h.name}</span>
              <span className="ram-gb">{h.gb} GB</span>
              <button className="ram-btn danger" disabled={busy === h.name}
                onClick={() => close(h.name)}>
                {busy === h.name ? 'closing…' : 'Close'}
              </button>
            </div>
          ))}
          {msg && <div className="ram-msg">{msg}</div>}
          <div className="ram-muted">Only your apps are listed — Windows, ILLIP and Ollama are protected.</div>
        </div>
      )}
    </div>
  )
}
