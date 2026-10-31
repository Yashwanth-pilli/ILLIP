import React, { useEffect, useMemo, useRef, useState } from 'react'
import { setLoginPassword, logoutLocal } from './LoginGate.jsx'

async function handleLockClick() {
  let enabled = false
  try {
    const r = await fetch('/api/auth/status')
    enabled = (await r.json()).enabled
  } catch { /* backend down — treat as not enabled */ }
  if (!enabled) {
    const pw = window.prompt('Set a password to lock ILLIP (min 4 chars). Anyone opening ILLIP will need it. Personal data stays on this PC.')
    if (!pw) return
    try { await setLoginPassword(pw); window.alert('Login enabled. ILLIP will ask for this password from now on.') }
    catch (e) { window.alert('Could not set password: ' + e.message) }
  } else if (window.confirm('Log out of ILLIP now? You will need the password to get back in.')) logoutLocal()
}

function SafetyBadge({ hwLive }) {
  if (!hwLive || hwLive.gpu_temp_c == null) return null
  const temp = hwLive.gpu_temp_c
  const pressure = hwLive.pressure || 'low'
  const map = {
    low: { cls: 'safe', label: 'Safe' }, medium: { cls: 'warm', label: 'Busy' },
    high: { cls: 'warm', label: 'Warm' }, critical: { cls: 'hot', label: 'Cooling' },
  }
  const s = map[pressure] || map.low
  const ramPct = hwLive.ram_percent || 0
  if (ramPct >= 90) return <span className="safety-badge warm" title={`RAM ${ramPct.toFixed(0)}% full. Close other apps to improve performance.`}>RAM {ramPct.toFixed(0)}%</span>
  return <span className={`safety-badge ${s.cls}`} title={`GPU ${temp.toFixed(0)}°C · ${s.label}`}>{temp > 0 ? `${temp.toFixed(0)}°C · ${s.label}` : 'CPU · Active'}</span>
}

export default function Header({
  connected, statusText, modelsData, pinnedModel, ghostBadge, dismissedSuggestion,
  projects, activeProject, hwLive, isLoading, onSwitchModel, onSwitchProject,
  onDismissSuggestion, onNewProject, onRefresh, onAutoSpeak, autoSpeak,
  onDeleteProject, theme = 'light', onToggleTheme, onOpenPanel,
}) {
  const [search, setSearch] = useState('')
  const [searchOpen, setSearchOpen] = useState(false)
  const searchRef = useRef(null)
  const normalized = search.trim().toLowerCase()
  const options = useMemo(() => {
    const base = [
      { label: 'Chat history', hint: 'Browse previous conversations', action: () => onOpenPanel?.('chats') },
      { label: 'Projects', hint: 'Open project workspace', action: () => onOpenPanel?.('workspace') },
      { label: 'Agents', hint: 'Open agent skills', action: () => onOpenPanel?.('skills') },
      { label: 'Tools', hint: 'Open connected tools', action: () => onOpenPanel?.('plugins') },
      { label: 'System status', hint: 'Hardware and connection health', action: () => onOpenPanel?.('system') },
      { label: 'Models & engines', hint: 'Installed models and engine settings', action: () => onOpenPanel?.('models') },
    ]
    ;(projects || []).forEach(p => base.push({ label: p.name, hint: 'Switch project', action: () => onSwitchProject?.(p.id) }))
    ;(modelsData?.models || []).forEach(m => base.push({ label: m.name, hint: 'Switch AI model', action: () => onSwitchModel?.(m.name) }))
    return base
  }, [projects, modelsData, onOpenPanel, onSwitchProject, onSwitchModel])
  const matches = options.filter(o => !normalized || `${o.label} ${o.hint}`.toLowerCase().includes(normalized)).slice(0, 7)
  const choose = (item) => { item.action(); setSearch(''); setSearchOpen(false); searchRef.current?.blur() }

  useEffect(() => {
    const onKey = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault(); setSearchOpen(true); searchRef.current?.focus()
      }
      if (e.key === 'Escape') setSearchOpen(false)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  const suggestion = !dismissedSuggestion && modelsData?.recommended && modelsData?.active &&
    modelsData.recommended.split(':')[0] !== modelsData.active.split(':')[0] ? modelsData : null

  return (
    <>
      <header className="app-header illip-topbar">
        <div className="header-controls">
          <div className="header-model-group">
            <select className="model-select-header" value={pinnedModel || ''} onChange={e => onSwitchModel(e.target.value || null)} aria-label="Select model">
              <option value="">Auto</option>
              {(modelsData?.models || []).map(m => <option key={m.name} value={m.name}>{m.name}{m.is_recommended ? ' (recommended)' : ''}</option>)}
            </select>
            {ghostBadge?.text && <span className={`ghost-badge ${ghostBadge.cls}`}>{ghostBadge.text}</span>}
          </div>
          <div className={`provider-chip ${connected ? 'online' : 'offline'}`} title={statusText || 'Ollama connection status'}>
            <span className="status-dot" /> <span>Ollama <small>(Local)</small></span>
          </div>
          <div className="global-search-wrap">
            <span className="global-search-icon">⌕</span>
            <input ref={searchRef} value={search} onFocus={() => setSearchOpen(true)} onChange={e => { setSearch(e.target.value); setSearchOpen(true) }} onKeyDown={e => { if (e.key === 'Enter' && matches[0]) { e.preventDefault(); choose(matches[0]) } }} placeholder="Search chats, projects, tools…" aria-label="Search chats, projects and tools" />
            <kbd>Ctrl K</kbd>
            {searchOpen && (
              <div className="global-search-results">
                <div className="global-search-caption">{normalized ? 'Matching destinations' : 'Quick navigation'}</div>
                {matches.length ? matches.map((item, i) => <button key={`${item.label}-${i}`} onMouseDown={e => e.preventDefault()} onClick={() => choose(item)}><span>{item.label}</span><small>{item.hint}</small></button>) : <p>No matching destination</p>}
              </div>
            )}
          </div>
          <div className="topbar-project-wrap">
            <select className="project-select" value={activeProject} onChange={e => onSwitchProject(e.target.value)} aria-label="Active project">
              {(projects || []).map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
              {!projects?.length && <option value="default">Default</option>}
            </select>
            <button className="icon-btn topbar-add" onClick={onNewProject} title="New project">＋</button>
          </div>
        </div>
        <div className="header-right">
          <div className="topbar-health"><span className={`status-dot ${connected ? '' : 'offline'}`} /><strong>{connected ? 'Local · Healthy' : 'Connecting…'}</strong><SafetyBadge hwLive={hwLive} /></div>
          <button className="theme-toggle" onClick={onToggleTheme} title={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`} aria-label="Toggle theme">{theme === 'light' ? '☾' : '☀'}</button>
          <button className="topbar-icon" onClick={() => onOpenPanel?.('governance')} title="Notifications">♧</button>
          <button className="topbar-icon" onClick={() => onOpenPanel?.('system')} title="Settings and system status">⚙</button>
          <button className="topbar-avatar" onClick={() => onOpenPanel?.('system')} title="Local workspace profile">K</button>
          <div className="topbar-legacy-actions">
            <button className="mode-btn refresh-btn" onClick={onRefresh} title="Refresh context">Refresh</button>
            <button className="mode-btn" onClick={handleLockClick} title="Lock ILLIP or log out">Lock</button>
            <button className={`mode-btn ${autoSpeak ? 'active' : ''}`} onClick={onAutoSpeak} title="Auto-speak responses">Speak</button>
            {activeProject !== 'default' && <button className="icon-btn" onClick={() => onDeleteProject(activeProject)} title="Delete project">✕</button>}
          </div>
        </div>
      </header>
      {searchOpen && <button className="search-dismiss-layer" aria-label="Close search" onClick={() => setSearchOpen(false)} />}
      {suggestion && <div className="model-suggestion"><span>{modelsData.hardware_summary} → best match: <strong>{modelsData.recommended}</strong></span><button className="suggestion-btn" onClick={() => onSwitchModel(modelsData.recommended)}>Switch model</button><button className="suggestion-dismiss" onClick={onDismissSuggestion}>✕</button></div>}
    </>
  )
}
