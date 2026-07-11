// Local-login client plumbing: stores the session token and attaches it to
// every same-origin /api and /v1 request (fetch + EventSource). When no
// password is set on the backend, there's simply no token and nothing changes.

const TOKEN_KEY = 'illip_token'

export const getToken = () => localStorage.getItem(TOKEN_KEY) || ''
export const setToken = (t) => { if (t) localStorage.setItem(TOKEN_KEY, t) }
export const clearToken = () => localStorage.removeItem(TOKEN_KEY)

const isApiPath = (url) => {
  try {
    const p = url.startsWith('http') ? new URL(url).pathname : url
    return p.startsWith('/api') || p.startsWith('/v1')
  } catch { return false }
}

// Patch fetch + EventSource once, so all existing api.js calls get the token
// with zero changes to each call site.
export function installAuthInterceptor() {
  if (window.__illipAuthPatched) return
  window.__illipAuthPatched = true

  const origFetch = window.fetch.bind(window)
  window.fetch = (input, init = {}) => {
    const url = typeof input === 'string' ? input : (input && input.url) || ''
    const token = getToken()
    if (token && isApiPath(url)) {
      const headers = new Headers((init && init.headers) || (typeof input !== 'string' && input.headers) || {})
      if (!headers.has('Authorization')) headers.set('Authorization', `Bearer ${token}`)
      init = { ...init, headers }
    }
    return origFetch(input, init)
  }

  // EventSource can't set headers → pass the token as a query param instead
  // (the auth middleware also accepts ?token=).
  const OrigES = window.EventSource
  if (OrigES) {
    window.EventSource = function (url, config) {
      const token = getToken()
      if (token && isApiPath(url)) {
        url += (url.includes('?') ? '&' : '?') + 'token=' + encodeURIComponent(token)
      }
      return new OrigES(url, config)
    }
    window.EventSource.prototype = OrigES.prototype
  }
}
