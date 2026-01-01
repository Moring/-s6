import { parseAdminCommand } from '../src/chat/commandParser'

describe('command parser', () => {
  it('parses create passkey', () => {
    const result = parseAdminCommand('create passkey expires=2025-01-01 tenant=2 max_uses=3')
    expect(result.action).toBe('admin.create_passkey')
    expect(result.params).toEqual({
      expires: '2025-01-01',
      tenant: '2',
      max_uses: '3',
    })
  })

  it('parses list users', () => {
    const result = parseAdminCommand('list users search=alice is_active=true')
    expect(result.action).toBe('admin.list_users')
    expect(result.params).toEqual({ search: 'alice', is_active: 'true' })
  })

  it('parses enable and disable user', () => {
    const enable = parseAdminCommand('enable user 42')
    expect(enable.action).toBe('admin.update_user')
    expect(enable.params).toEqual({ id: '42', is_active: true })

    const disable = parseAdminCommand('disable user 7 reason="policy"')
    expect(disable.action).toBe('admin.update_user')
    expect(disable.params).toEqual({ id: '7', is_active: false, disable_reason: 'policy' })
  })

  it('parses password reset', () => {
    const result = parseAdminCommand('reset password 9 new-pass')
    expect(result.action).toBe('admin.reset_password')
    expect(result.params).toEqual({ id: '9', new_password: 'new-pass' })
  })
})
