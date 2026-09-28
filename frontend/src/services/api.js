const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'
const SESSION_KEY = 'fieldnote.session'

export function getSession() {
  try { return JSON.parse(localStorage.getItem(SESSION_KEY)) } catch { return null }
}
export function saveSession(session) { localStorage.setItem(SESSION_KEY, JSON.stringify(session)) }
export function clearSession() { localStorage.removeItem(SESSION_KEY) }

export async function api(path, { method = 'GET', body, headers = {}, auth = true, raw = false } = {}) {
  const session = getSession()
  const requestHeaders = { ...headers }
  if (!(body instanceof FormData) && body !== undefined) requestHeaders['Content-Type'] = 'application/json'
  if (auth && session?.access_token) requestHeaders.Authorization = `Bearer ${session.access_token}`
  const response = await fetch(`${API_BASE}${path}`, { method, headers: requestHeaders, body: body instanceof FormData ? body : body === undefined ? undefined : JSON.stringify(body) })
  if (raw) {
    if (!response.ok) throw new Error((await response.json()).detail || 'The request could not be completed.')
    return response
  }
  if (response.status === 204) return null
  const result = await response.json().catch(() => ({}))
  if (!response.ok) {
    if (response.status === 401 && auth) clearSession()
    throw new Error(result.detail || 'The request could not be completed.')
  }
  return result
}