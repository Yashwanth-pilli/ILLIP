import React, { useEffect } from 'react'
import { marked } from 'marked'

// Ephemeral overlay for diagnostics/repair (/doctor, /heal). Results show here,
// NOT in chat history — run it, read it, dismiss it, chat stays clean.
export default function DiagnosticPanel({ title, md, busy, onClose, onRerun, rerunLabel }) {
  useEffect(() => {
    const onKey = e => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <div className="diag-overlay" onClick={onClose}>
      <div className="diag-panel" onClick={e => e.stopPropagation()}>
        <div className="diag-header">
          <span className="diag-title">{title}</span>
          <div className="diag-header-btns">
            {onRerun && (
              <button className="diag-rerun" onClick={onRerun} disabled={busy}>
                {busy ? '…' : (rerunLabel || '↻ Run again')}
              </button>
            )}
            <button className="diag-close" onClick={onClose}>✕</button>
          </div>
        </div>
        <div className="diag-body">
          {busy && !md
            ? <p className="diag-loading">Running…</p>
            : <div dangerouslySetInnerHTML={{ __html: marked.parse(md || '') }} />}
        </div>
      </div>
    </div>
  )
}
