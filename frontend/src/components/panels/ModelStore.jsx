import React, { useState, useEffect, useCallback } from 'react'
import { api } from '../../api.js'

const FIT = {
  'full-gpu': { label: '✅ Fits your GPU', color: '#22c55e' },
  'partial':  { label: '🟡 Runs — GPU+RAM split', color: '#f59e0b' },
  'cpu':      { label: '🟡 Runs on CPU (slower)', color: '#f59e0b' },
  'too-big':  { label: '❌ Too big for this machine', color: '#ef4444' },
}

// Curated model store: what to download for THIS machine, with disk guard
// and live pull progress. Used in the Models panel and the first-run wizard.
export default function ModelStore({ onInstalled, recommendedOnly = false }) {
  const [data, setData] = useState(null)
  const [pulling, setPulling] = useState({})   // name -> {pct, status}
  const [err, setErr] = useState('')

  const load = useCallback(async () => {
    try { setData(await api.modelCatalog()) } catch { setData({ catalog: [], error: true }) }
  }, [])
  useEffect(() => { load() }, [load])

  const pull = async (name) => {
    setErr('')
    setPulling(p => ({ ...p, [name]: { pct: 0, status: 'starting…' } }))
    try {
      await api.modelPull(name, (ev) => {
        if (ev.error) throw new Error(ev.error)
        const pct = ev.total ? Math.round(((ev.completed || 0) / ev.total) * 100) : null
        setPulling(p => ({ ...p, [name]: { pct, status: ev.status || '' } }))
      })
      setPulling(p => { const q = { ...p }; delete q[name]; return q })
      await load()
      onInstalled && onInstalled(name)
    } catch (e) {
      setErr(String(e.message || e))
      setPulling(p => { const q = { ...p }; delete q[name]; return q })
    }
  }

  if (!data) return <p className="status-label">Loading catalog…</p>

  let items = (data.catalog || []).filter(m => !m.installed)
  if (recommendedOnly && data.recommended_download) {
    items = items.filter(m => m.name === data.recommended_download)
  }

  return (
    <div>
      {!data.ollama_running && (
        <p style={{ color: '#f59e0b', fontSize: '12px' }}>
          Ollama isn't running — downloads need it. Install from{' '}
          <a href="https://ollama.com" target="_blank" rel="noreferrer">ollama.com</a>, then reopen.
        </p>
      )}
      {err && <p style={{ color: '#ef4444', fontSize: '12px' }}>{err}</p>}
      {items.map(m => {
        const fit = FIT[m.fit] || FIT.cpu
        const pr = pulling[m.name]
        const isRec = m.name === data.recommended_download
        return (
          <div key={m.name} className="model-item" style={{ cursor: 'default' }}>
            <div className="model-name">
              {m.name}{isRec ? ' ⭐ recommended' : ''}
            </div>
            <div style={{ fontSize: '12px', color: 'var(--text2, #94a3b8)', margin: '2px 0' }}>{m.blurb}</div>
            <div className="model-meta">
              <span style={{ color: fit.color }}>{fit.label}</span>
              <span>{m.size_gb}GB download</span>
            </div>
            {pr ? (
              <div style={{ fontSize: '12px', marginTop: '4px' }}>
                <div style={{ height: '6px', background: 'rgba(255,255,255,.08)', borderRadius: '3px', overflow: 'hidden' }}>
                  <div style={{ height: '100%', width: `${pr.pct ?? 5}%`, background: '#4fd1c5', transition: 'width .3s' }} />
                </div>
                <span>{pr.pct != null ? `${pr.pct}%` : ''} {pr.status}</span>
              </div>
            ) : (
              <button
                className="btn-primary"
                style={{ marginTop: '4px', fontSize: '12px', padding: '3px 10px' }}
                disabled={m.fit === 'too-big' || !data.ollama_running}
                onClick={() => pull(m.name)}
              >
                ⬇ Download
              </button>
            )}
          </div>
        )
      })}
      {!items.length && <p className="status-label">Everything in the catalog that fits is already installed. 🎉</p>}
      <div style={{ fontSize: '11px', color: 'var(--text2, #94a3b8)', marginTop: '8px' }}>
        {data.hardware_summary} · {data.free_disk_gb}GB disk free
      </div>
    </div>
  )
}
