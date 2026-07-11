import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import ErrorBoundary from './ErrorBoundary.jsx'
import LoginGate from './components/LoginGate.jsx'
import { installAuthInterceptor } from './auth-client.js'
import './styles.css'

// Attach the session token to every /api + /v1 request before anything renders.
installAuthInterceptor()

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ErrorBoundary>
      <LoginGate>
        <App />
      </LoginGate>
    </ErrorBoundary>
  </React.StrictMode>,
)
