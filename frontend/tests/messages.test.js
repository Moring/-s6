import { LOGIN_FAILED_MESSAGE, SIGNUP_FAILED_MESSAGE } from '../src/chat/messages'

describe('no user enumeration messages', () => {
  it('matches required login failure message', () => {
    expect(LOGIN_FAILED_MESSAGE).toBe(
      'We do not recognize that username and password. Please try again.'
    )
  })

  it('matches required signup failure message', () => {
    expect(SIGNUP_FAILED_MESSAGE).toBe(
      "Signup could not be completed. Please verify your invite passkey and credentials, or try 'login'."
    )
  })
})
