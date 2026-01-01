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

export const request = async (method, path, body, options = {}) => {
  const headers = {
    Accept: 'application/json',
    ...(options.headers || {}),
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
