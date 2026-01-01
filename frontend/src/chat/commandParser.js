const parseKeyValuePairs = (input) => {
  const params = {}
  const regex = /(\w+)=(".*?"|'.*?'|\S+)/g
  let match = regex.exec(input)
  while (match) {
    const key = match[1]
    let value = match[2]
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1)
    }
    params[key] = value
    match = regex.exec(input)
  }
  return params
}

const normalize = (value) => value.trim().toLowerCase()

const extractFirstToken = (value) => {
  const [token, ...rest] = value.trim().split(/\s+/)
  return { token, rest: rest.join(' ') }
}

export const parseAdminCommand = (input) => {
  const trimmed = input.trim()
  if (!trimmed) {
    return null
  }

  const lower = normalize(trimmed)

  if (['admin help', 'help admin', 'admin commands'].includes(lower)) {
    return { action: 'admin.help', params: {} }
  }

  if (lower.startsWith('create passkey') || lower.startsWith('passkey create')) {
    const params = parseKeyValuePairs(trimmed)
    return { action: 'admin.create_passkey', params }
  }

  if (lower.startsWith('list users')) {
    const params = parseKeyValuePairs(trimmed)
    return { action: 'admin.list_users', params }
  }

  if (lower.startsWith('search users')) {
    const term = trimmed.replace(/search users/i, '').trim()
    return { action: 'admin.list_users', params: { search: term } }
  }

  if (lower.startsWith('enable user')) {
    const { token } = extractFirstToken(trimmed.replace(/enable user/i, ''))
    return { action: 'admin.update_user', params: { id: token, is_active: true } }
  }

  if (lower.startsWith('disable user')) {
    const raw = trimmed.replace(/disable user/i, '')
    const { token, rest } = extractFirstToken(raw)
    const params = parseKeyValuePairs(rest)
    return {
      action: 'admin.update_user',
      params: { id: token, is_active: false, disable_reason: params.reason },
    }
  }

  if (lower.startsWith('reset password') || lower.startsWith('reset user password')) {
    const raw = trimmed.replace(/reset user password|reset password/i, '')
    const { token, rest } = extractFirstToken(raw)
    const newPassword = rest.trim()
    return {
      action: 'admin.reset_password',
      params: { id: token, new_password: newPassword },
    }
  }

  if (lower.startsWith('view user')) {
    const target = trimmed.replace(/view user/i, '').trim()
    return { action: 'admin.view_user', params: { search: target } }
  }

  if (lower.startsWith('update user') || lower.startsWith('edit user')) {
    const raw = trimmed.replace(/update user|edit user/i, '')
    const { token, rest } = extractFirstToken(raw)
    const params = parseKeyValuePairs(rest)
    return {
      action: 'admin.update_user',
      params: { id: token, ...params },
    }
  }

  return null
}
