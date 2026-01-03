import { getAccessToken, setAccessToken, clearAuth } from '../store/state'

const API_BASE = '/api'

const getCookie = (name) => {
  if (typeof document === 'undefined') {
    return null
  }
  const cookies = document.cookie ? document.cookie.split('; ') : []
  for (const cookie of cookies) {
    const [key, ...rest] = cookie.split('=')
    if (key === name) {
      return decodeURIComponent(rest.join('='))
    }
  }
  return null
}

const shouldAttachCsrf = (method) => !['GET', 'HEAD', 'OPTIONS'].includes(method.toUpperCase())

const refreshAccessToken = async () => {
  const response = await fetch(`${API_BASE}/auth/token/refresh/`, {
    method: 'POST',
    headers: { Accept: 'application/json' },
    credentials: 'include',
  })

  if (!response.ok) {
    clearAuth()
    return false
  }

  const text = await response.text()
  if (!text) {
    setAccessToken(null)
    return false
  }

  let data = null
  try {
    data = JSON.parse(text)
  } catch {
    data = null
  }
  if (!data || !data.access) {
    clearAuth()
    return false
  }

  setAccessToken(data.access)
  return true
}

export const request = async (method, path, body, options = {}) => {
  const headers = {
    Accept: 'application/json',
    ...(options.headers || {}),
  }

  const authToken = getAccessToken()
  if (authToken && !options.skipAuth) {
    headers.Authorization = `Bearer ${authToken}`
  }

  if (body) {
    headers['Content-Type'] = 'application/json'
  }

  if (options.etag) {
    headers['If-None-Match'] = options.etag
  }

  if (shouldAttachCsrf(method)) {
    const csrfToken = getCookie('csrftoken')
    if (csrfToken) {
      headers['X-CSRFToken'] = csrfToken
    }
  }

  const response = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    credentials: 'include',
    body: body ? JSON.stringify(body) : undefined,
  })

  const etag = response.headers.get('ETag')

  if (response.status === 304) {
    return { notModified: true, status: response.status, etag }
  }

  if (response.status === 401 && !options.skipAuthRefresh) {
    const refreshed = await refreshAccessToken()
    if (refreshed) {
      return request(method, path, body, { ...options, skipAuthRefresh: true })
    }
  }

  const text = await response.text()
  let data = null
  if (text) {
    try {
      data = JSON.parse(text)
    } catch {
      data = { message: text }
    }
  }

  if (!response.ok) {
    const message = data?.error || data?.message || `Request failed with status ${response.status}`
    const err = new Error(message)
    err.status = response.status
    err.data = data
    throw err
  }

  return { data, status: response.status, etag }
}
