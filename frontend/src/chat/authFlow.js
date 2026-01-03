export const AUTH_FLOW_MODES = {
  IDLE: 'idle',
  LOGIN: 'login',
  SIGNUP: 'signup',
}

export const LOGIN_STEPS = {
  USERNAME: 'username',
  PASSWORD: 'password',
}

export const SIGNUP_STEPS = {
  USERNAME: 'username',
  PASSWORD: 'password',
  CONFIRM: 'confirm',
  PASSKEY: 'passkey',
}

export const createAuthFlowState = () => ({
  mode: AUTH_FLOW_MODES.IDLE,
  step: null,
  data: {},
})

export const isAuthFlowActive = (flow) => flow.mode !== AUTH_FLOW_MODES.IDLE

export const beginAuthFlow = (mode) => {
  if (mode === AUTH_FLOW_MODES.LOGIN) {
    return {
      flow: { mode, step: LOGIN_STEPS.USERNAME, data: {} },
      prompt: 'Enter username:',
    }
  }

  if (mode === AUTH_FLOW_MODES.SIGNUP) {
    return {
      flow: { mode, step: SIGNUP_STEPS.USERNAME, data: {} },
      prompt: 'Enter username:',
    }
  }

  return { flow: createAuthFlowState(), prompt: null }
}

export const advanceAuthFlow = (flow, input) => {
  const trimmed = input.trim()
  if (!trimmed) {
    return { flow, prompt: null }
  }

  if (flow.mode === AUTH_FLOW_MODES.LOGIN) {
    if (flow.step === LOGIN_STEPS.USERNAME) {
      return {
        flow: { ...flow, step: LOGIN_STEPS.PASSWORD, data: { ...flow.data, username: trimmed } },
        prompt: 'Enter password:',
      }
    }

    if (flow.step === LOGIN_STEPS.PASSWORD) {
      return {
        flow: createAuthFlowState(),
        complete: {
          type: AUTH_FLOW_MODES.LOGIN,
          data: { ...flow.data, password: trimmed },
        },
      }
    }
  }

  if (flow.mode === AUTH_FLOW_MODES.SIGNUP) {
    if (flow.step === SIGNUP_STEPS.USERNAME) {
      return {
        flow: { ...flow, step: SIGNUP_STEPS.PASSWORD, data: { ...flow.data, username: trimmed } },
        prompt: 'Enter password:',
      }
    }

    if (flow.step === SIGNUP_STEPS.PASSWORD) {
      return {
        flow: { ...flow, step: SIGNUP_STEPS.CONFIRM, data: { ...flow.data, password: trimmed } },
        prompt: 'Confirm password:',
      }
    }

    if (flow.step === SIGNUP_STEPS.CONFIRM) {
      if (trimmed !== flow.data.password) {
        return {
          flow: { ...flow, step: SIGNUP_STEPS.PASSWORD },
          prompt: 'Passwords do not match. Enter password:',
          error: 'password_mismatch',
        }
      }

      return {
        flow: { ...flow, step: SIGNUP_STEPS.PASSKEY },
        prompt: 'Enter invite passkey:',
      }
    }

    if (flow.step === SIGNUP_STEPS.PASSKEY) {
      return {
        flow: createAuthFlowState(),
        complete: {
          type: AUTH_FLOW_MODES.SIGNUP,
          data: { ...flow.data, passkey: trimmed },
        },
      }
    }
  }

  return { flow, prompt: null }
}
