import Vue from 'vue'

import { createAuthFlowState } from '../chat/authFlow'
import { PROMPT_LOGGED_OUT } from '../chat/messages'

let messageId = 1

export const state = Vue.observable({
  auth: {
    user: null,
    isAuthenticated: false,
    isAdmin: false,
    accessToken: null,
  },
  chat: {
    messages: [
      {
        id: messageId,
        role: 'assistant',
        text: PROMPT_LOGGED_OUT,
        timestamp: new Date().toISOString(),
      },
    ],
    flow: createAuthFlowState(),
    isBusy: false,
  },
  canvas: {
    type: 'welcome',
    payload: {},
  },
  footer: {
    sessionTokens: 0,
    reserveBalance: null,
    updatedAt: null,
    isLowBalance: false,
    loading: false,
    error: null,
  },
})

export const addMessage = (role, text) => {
  messageId += 1
  state.chat.messages.push({
    id: messageId,
    role,
    text,
    timestamp: new Date().toISOString(),
  })
}

export const setChatBusy = (isBusy) => {
  state.chat.isBusy = isBusy
}

export const setChatFlow = (flow) => {
  Vue.set(state.chat, 'flow', flow)
}

export const resetChatFlow = () => {
  Vue.set(state.chat, 'flow', createAuthFlowState())
}

export const setCanvas = (type, payload = {}) => {
  Object.assign(state.canvas, { type, payload })
}

export const setAuth = (user) => {
  state.auth.user = user
  state.auth.isAuthenticated = Boolean(user)
  state.auth.isAdmin = Boolean(user && user.is_staff)
}

export const clearAuth = () => {
  state.auth.user = null
  state.auth.isAuthenticated = false
  state.auth.isAdmin = false
  state.auth.accessToken = null
}

export const setAccessToken = (token) => {
  state.auth.accessToken = token || null
}

export const getAccessToken = () => state.auth.accessToken

export const setFooterStatus = ({ sessionTokens, reserveBalance, updatedAt, isLowBalance }) => {
  state.footer.sessionTokens = sessionTokens
  state.footer.reserveBalance = reserveBalance
  state.footer.updatedAt = updatedAt
  state.footer.isLowBalance = Boolean(isLowBalance)
}

export const setFooterLoading = (loading) => {
  state.footer.loading = loading
}

export const setFooterError = (error) => {
  state.footer.error = error
}

export const resetFooter = () => {
  state.footer.sessionTokens = 0
  state.footer.reserveBalance = null
  state.footer.updatedAt = null
  state.footer.isLowBalance = false
  state.footer.loading = false
  state.footer.error = null
}
