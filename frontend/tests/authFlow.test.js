import { AUTH_FLOW_MODES, beginAuthFlow, advanceAuthFlow } from '../src/chat/authFlow'

describe('auth flow', () => {
  it('advances through login flow', () => {
    const start = beginAuthFlow(AUTH_FLOW_MODES.LOGIN)
    expect(start.prompt).toBe('Enter username:')

    const step1 = advanceAuthFlow(start.flow, 'alice')
    expect(step1.prompt).toBe('Enter password:')

    const step2 = advanceAuthFlow(step1.flow, 'super-secret')
    expect(step2.complete.type).toBe(AUTH_FLOW_MODES.LOGIN)
    expect(step2.complete.data).toEqual({
      username: 'alice',
      password: 'super-secret',
    })
  })

  it('handles signup password mismatch', () => {
    const start = beginAuthFlow(AUTH_FLOW_MODES.SIGNUP)
    const step1 = advanceAuthFlow(start.flow, 'newuser')
    const step2 = advanceAuthFlow(step1.flow, 'pw123')
    const step3 = advanceAuthFlow(step2.flow, 'pw456')

    expect(step3.prompt).toBe('Passwords do not match. Enter password:')
    expect(step3.flow.step).toBe('password')
  })

  it('completes signup flow', () => {
    const start = beginAuthFlow(AUTH_FLOW_MODES.SIGNUP)
    const step1 = advanceAuthFlow(start.flow, 'newuser')
    const step2 = advanceAuthFlow(step1.flow, 'pw123')
    const step3 = advanceAuthFlow(step2.flow, 'pw123')
    const step4 = advanceAuthFlow(step3.flow, 'invite-123')

    expect(step4.complete.type).toBe(AUTH_FLOW_MODES.SIGNUP)
    expect(step4.complete.data).toEqual({
      username: 'newuser',
      password: 'pw123',
      passkey: 'invite-123',
    })
  })
})
