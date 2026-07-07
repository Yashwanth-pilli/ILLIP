import React from 'react'
import ModelStore from '../panels/ModelStore.jsx'

// Shown once when ILLIP starts with no local models: explains what the
// machine can run and offers the recommended download. Skippable — cloud
// providers configured in .env still work without a local model.
export default function FirstRunWizard({ onDone }) {
  return (
    <div className="modal-overlay">
      <div className="modal-box" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h3 style={{ margin: 0 }}>👋 Welcome to ILLIP</h3>
        </div>
        <p style={{ fontSize: '13px' }}>
          No local AI model found yet. Pick one sized for your machine — it
          downloads once, then everything runs offline and private.
        </p>
        <ModelStore onInstalled={() => onDone(true)} />
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '10px' }}>
          <button className="btn-secondary" onClick={() => onDone(false)}>
            Skip — I'll use cloud models / set up later
          </button>
        </div>
      </div>
    </div>
  )
}
