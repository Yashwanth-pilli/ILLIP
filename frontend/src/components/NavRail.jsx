import React, { useState } from 'react'

const PRIMARY = [
  { id: 'activity', label: 'Chat', icon: '◷' },
  { id: 'workspace', label: 'Projects', icon: '▱' },
  { id: 'skills', label: 'Agents', icon: '♧' },
  { id: 'plugins', label: 'Tools', icon: '⌘' },
]
const MORE = [
  { id: 'chats', label: 'Chat history', icon: '◷' },
  { id: 'system', label: 'System status', icon: '⌁' },
  { id: 'models', label: 'Models & engines', icon: '◈' },
  { id: 'memory', label: 'Memory', icon: '⬡' },
  { id: 'scheduler', label: 'Scheduler', icon: '◷' },
  { id: 'governance', label: 'Approvals', icon: '◇' },
  { id: 'stats', label: 'Usage & stats', icon: '▥' },
]

export default function NavRail({ activePanel, onTogglePanel, onNewChat }) {
  const [moreOpen, setMoreOpen] = useState(false)
  const active = activePanel
  return (
    <nav className="nav-rail" aria-label="Main navigation">
      <div className="nav-brand-mini">
        <img src="/illip-logo.png" alt="ILLIP emblem" />
        <span>ILLIP</span><small>AI Agent OS</small>
      </div>
      <button className="nav-new-chat" onClick={onNewChat}><span className="new-chat-plus">＋</span><span>New chat</span><kbd>Ctrl N</kbd></button>
      <div className="nav-primary">
        {PRIMARY.map(item => <button key={item.id} className={`nav-btn ${active === item.id ? 'active' : ''}`} onClick={() => { setMoreOpen(false); onTogglePanel(item.id) }}><span className="nav-icon">{item.icon}</span><span>{item.label}</span></button>)}
      </div>
      <div className="nav-divider" />
      <button className={`nav-btn nav-more ${moreOpen || MORE.some(x => x.id === activePanel) ? 'active' : ''}`} onClick={() => setMoreOpen(v => !v)} aria-expanded={moreOpen}><span className="nav-icon">···</span><span>More</span><span className="nav-chevron">{moreOpen ? '⌄' : '›'}</span></button>
      {moreOpen && <div className="nav-more-menu">{MORE.map(item => <button key={item.id} className={activePanel === item.id ? 'selected' : ''} onClick={() => { setMoreOpen(false); onTogglePanel(item.id) }}><span>{item.icon}</span>{item.label}</button>)}</div>}
      <div className="nav-spacer" />
      <div className="nav-service-status">
        <div><i /> <span>Ollama</span><b>Local</b></div>
        <div><i /> <span>OmniRoute</span><b>Connected</b></div>
      </div>
      <div className="nav-profile"><span>K</span><div><strong>Local workspace</strong><small>Private · on this device</small></div><b>›</b></div>
    </nav>
  )
}
