import { request } from './client'

const buildQueryString = (params = {}) => {
  const query = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') {
      return
    }
    query.set(key, value)
  })
  const queryString = query.toString()
  return queryString ? `?${queryString}` : ''
}

export const authApi = {
  login: ({ username, password }) =>
    request(
      'POST',
      '/auth/login/',
      {
        username,
        password,
      },
      { skipAuth: true, skipAuthRefresh: true }
    ),
  signup: ({ username, email, password, passkey }) =>
    request(
      'POST',
      '/auth/signup/',
      {
        username,
        email,
        password,
        passkey,
      },
      { skipAuth: true, skipAuthRefresh: true }
    ),
  refresh: () => request('POST', '/auth/token/refresh/', null, { skipAuth: true, skipAuthRefresh: true }),
  logout: () => request('POST', '/auth/logout/'),
  me: () => request('GET', '/me/'),
}

export const statusApi = {
  get: (etag) => request('GET', '/status/bar/', null, { etag }),
}

export const adminApi = {
  createPasskey: (payload) => request('POST', '/admin/passkeys/', payload),
  listUsers: (params) => request('GET', `/admin/users/${buildQueryString(params)}`),
  updateUser: (id, payload) => request('PATCH', `/admin/users/${id}/`, payload),
  resetPassword: (id, payload) =>
    request('POST', `/admin/users/${id}/reset-password/`, payload),
}
