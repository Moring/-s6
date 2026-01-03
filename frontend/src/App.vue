<template>
  <div class="afterresume-shell">
    <div class="afterresume-main">
      <ChatPanel
        :messages="state.chat.messages"
        :busy="state.chat.isBusy"
        :status-label="chatStatusLabel"
        @send="handleSend"
      />
      <CanvasPanel :canvas="state.canvas" :updated-at="state.footer.updatedAt" />
    </div>
    <FooterBar
      :session-tokens="state.footer.sessionTokens"
      :reserve-balance="state.footer.reserveBalance"
      :updated-at="footerUpdatedLabel"
      :is-low-balance="state.footer.isLowBalance"
      :loading="state.footer.loading"
      :error="state.footer.error"
    />
  </div>
</template>

<script>
import ChatPanel from './components/ChatPanel.vue'
import CanvasPanel from './components/CanvasPanel.vue'
import FooterBar from './components/FooterBar.vue'

import {
  state,
  addMessage,
  setChatBusy,
  setChatFlow,
  resetChatFlow,
  setCanvas,
  setAuth,
  setAccessToken,
  getAccessToken,
  clearAuth,
  setFooterStatus,
  setFooterLoading,
  setFooterError,
  resetFooter,
} from './store/state'
import { AUTH_FLOW_MODES, beginAuthFlow, advanceAuthFlow, isAuthFlowActive } from './chat/authFlow'
import { parseAdminCommand } from './chat/commandParser'
import {
  AUTH_REQUIRED_MESSAGE,
  LOGIN_FAILED_MESSAGE,
  NOT_AUTHORIZED_MESSAGE,
  SIGNUP_FAILED_MESSAGE,
  UNKNOWN_COMMAND_MESSAGE,
} from './chat/messages'
import { adminApi, authApi, statusApi } from './api'

const STATUS_REFRESH_MS = 60000

export default {
  name: 'App',
  components: {
    ChatPanel,
    CanvasPanel,
    FooterBar,
  },
  data() {
    return {
      state,
      statusTimer: null,
      statusEtag: null,
    }
  },
  computed: {
    chatStatusLabel() {
      if (this.state.auth.isAuthenticated && this.state.auth.user) {
        return `Signed in: ${this.state.auth.user.username}`
      }
      return 'Signed out'
    },
    footerUpdatedLabel() {
      if (!this.state.footer.updatedAt) {
        return null
      }
      return new Date(this.state.footer.updatedAt).toLocaleTimeString()
    },
  },
  created() {
    this.bootstrapSession()
  },
  beforeDestroy() {
    this.stopStatusPolling()
  },
  methods: {
    async bootstrapSession() {
      try {
        const refreshed = await authApi.refresh()
        if (refreshed?.data?.access) {
          setAccessToken(refreshed.data.access)
        }
      } catch (error) {
        if (error.status && ![400, 401].includes(error.status)) {
          addMessage('assistant', 'Unable to restore session. Please login.')
          setCanvas('auth-error', { message: 'Unable to restore session.' })
        }
      }

      if (!getAccessToken()) {
        this.promptLogin()
        return
      }

      try {
        const response = await authApi.me()
        const user = response.data
        setAuth(user)
        addMessage('assistant', `Welcome back, ${user.username}.`)
        setCanvas('dashboard', {
          user,
          sessionTokens: this.state.footer.sessionTokens,
          reserveBalance: this.state.footer.reserveBalance,
        })
        await this.refreshStatus()
        this.startStatusPolling()
      } catch (error) {
        clearAuth()
        if (error.status && error.status !== 401) {
          addMessage('assistant', 'Unable to verify session. Please login.')
          setCanvas('auth-error', { message: 'Unable to verify session.' })
        }
        this.promptLogin()
      }
    },
    async handleSend(text) {
      addMessage('user', text)

      if (isAuthFlowActive(this.state.chat.flow)) {
        await this.handleAuthFlowInput(text)
        return
      }

      const normalized = text.trim().toLowerCase()

      if (!this.state.auth.isAuthenticated) {
        if (normalized === 'signup') {
          this.startAuthFlow(AUTH_FLOW_MODES.SIGNUP)
          return
        }
        if (!isAuthFlowActive(this.state.chat.flow)) {
          const { flow } = beginAuthFlow(AUTH_FLOW_MODES.LOGIN)
          setChatFlow(flow)
        }
        await this.handleAuthFlowInput(text)
        return
      }

      if (normalized === 'logout') {
        await this.performLogout()
        return
      }

      const adminCommand = parseAdminCommand(text)
      if (adminCommand) {
        if (!this.state.auth.isAdmin) {
          addMessage('assistant', NOT_AUTHORIZED_MESSAGE)
          setCanvas('not-authorized', { message: NOT_AUTHORIZED_MESSAGE })
          return
        }
        await this.executeAdminCommand(adminCommand)
        return
      }

      if (normalized === 'help') {
        addMessage(
          'assistant',
          "Try 'logout' or 'admin help' for administrative actions."
        )
        return
      }

      addMessage('assistant', UNKNOWN_COMMAND_MESSAGE)
    },
    startAuthFlow(mode) {
      const { flow, prompt } = beginAuthFlow(mode)
      setChatFlow(flow)
      if (prompt) {
        addMessage('assistant', prompt)
      }
    },
    async handleAuthFlowInput(text) {
      const result = advanceAuthFlow(this.state.chat.flow, text)
      if (result.flow) {
        setChatFlow(result.flow)
      }
      if (result.prompt) {
        addMessage('assistant', result.prompt)
      }
      if (result.complete?.type === AUTH_FLOW_MODES.LOGIN) {
        await this.performLogin(result.complete.data)
      }
      if (result.complete?.type === AUTH_FLOW_MODES.SIGNUP) {
        await this.performSignup(result.complete.data)
      }
    },
    async performLogin(payload) {
      setChatBusy(true)
      setCanvas('loading', { title: 'Signing in...' })
      try {
        const response = await authApi.login({
          username: payload.username,
          password: payload.password,
        })
        if (response.data.access) {
          setAccessToken(response.data.access)
        }
        const user = response.data.user || response.data
        setAuth(user)
        this.statusEtag = null
        addMessage('assistant', `Login successful. Welcome, ${user.username}.`)
        setCanvas('dashboard', {
          user,
          sessionTokens: this.state.footer.sessionTokens,
          reserveBalance: this.state.footer.reserveBalance,
        })
        await this.refreshStatus()
        this.startStatusPolling()
      } catch {
        addMessage('assistant', LOGIN_FAILED_MESSAGE)
        setCanvas('auth-error', { message: LOGIN_FAILED_MESSAGE })
      } finally {
        if (!this.state.auth.isAuthenticated) {
          this.promptLogin()
        } else {
          resetChatFlow()
        }
        setChatBusy(false)
      }
    },
    async performSignup(payload) {
      setChatBusy(true)
      setCanvas('loading', { title: 'Creating account...' })
      try {
        const email = this.deriveEmail(payload.username)
        const response = await authApi.signup({
          username: payload.username,
          email,
          password: payload.password,
          passkey: payload.passkey,
        })
        if (response.data.access) {
          setAccessToken(response.data.access)
        }
        const user = response.data.user || response.data
        setAuth(user)
        this.statusEtag = null
        addMessage('assistant', `Signup complete. Welcome, ${user.username}.`)
        setCanvas('dashboard', {
          user,
          sessionTokens: this.state.footer.sessionTokens,
          reserveBalance: this.state.footer.reserveBalance,
        })
        await this.refreshStatus()
        this.startStatusPolling()
      } catch {
        addMessage('assistant', SIGNUP_FAILED_MESSAGE)
        setCanvas('auth-error', { message: SIGNUP_FAILED_MESSAGE })
      } finally {
        if (!this.state.auth.isAuthenticated) {
          this.promptLogin()
        } else {
          resetChatFlow()
        }
        setChatBusy(false)
      }
    },
    async performLogout() {
      setChatBusy(true)
      setCanvas('loading', { title: 'Signing out...' })
      try {
        await authApi.logout()
      } catch {
        // Ignore logout errors to ensure local reset.
      } finally {
        clearAuth()
        resetFooter()
        resetChatFlow()
        this.stopStatusPolling()
        this.statusEtag = null
        addMessage('assistant', 'Logged out.')
        setCanvas('not-logged-in', { message: AUTH_REQUIRED_MESSAGE })
        setChatBusy(false)
      }
    },
    promptLogin() {
      setCanvas('not-logged-in', { message: AUTH_REQUIRED_MESSAGE })
      const { flow, prompt } = beginAuthFlow(AUTH_FLOW_MODES.LOGIN)
      setChatFlow(flow)
      if (prompt) {
        addMessage('assistant', prompt)
      }
    },
    async executeAdminCommand(command) {
      setChatBusy(true)
      setCanvas('loading', { title: 'Running admin command...' })
      try {
        switch (command.action) {
          case 'admin.help':
            setCanvas('admin-help', {})
            addMessage('assistant', 'Admin command list refreshed on the canvas.')
            break
          case 'admin.create_passkey': {
            const payload = {
              expires_at: command.params.expires || command.params.expires_at,
              tenant_scope: command.params.tenant,
              max_uses: command.params.max_uses ? Number(command.params.max_uses) : undefined,
              notes: command.params.notes,
            }
            const response = await adminApi.createPasskey(payload)
            setCanvas('admin-passkey', {
              passkey: response.data.passkey,
              rawKey: response.data.raw_key,
            })
            addMessage('assistant', 'Passkey created.')
            break
          }
          case 'admin.list_users': {
            const params = {
              search: command.params.search,
              is_active: command.params.is_active,
            }
            const response = await adminApi.listUsers(params)
            setCanvas('admin-users', { users: response.data.users })
            addMessage('assistant', `Found ${response.data.count} users.`)
            break
          }
          case 'admin.view_user': {
            const response = await adminApi.listUsers({ search: command.params.search })
            const user = response.data.users?.[0]
            if (user) {
              setCanvas('admin-user', { user })
              addMessage('assistant', `Showing user ${user.username}.`)
            } else {
              setCanvas('admin-user', { user: { message: 'User not found.' } })
              addMessage('assistant', 'User not found.')
            }
            break
          }
          case 'admin.update_user': {
            if (!command.params.id) {
              addMessage('assistant', 'User id is required.')
              break
            }
            const payload = this.buildUserUpdatePayload(command.params)
            const response = await adminApi.updateUser(command.params.id, payload)
            setCanvas('admin-update', {
              message: response.data.message,
              user: response.data.user,
            })
            addMessage('assistant', response.data.message)
            break
          }
          case 'admin.reset_password': {
            if (!command.params.id || !command.params.new_password) {
              addMessage('assistant', 'User id and new password are required.')
              break
            }
            const response = await adminApi.resetPassword(command.params.id, {
              new_password: command.params.new_password,
            })
            setCanvas('admin-reset', { message: response.data.message })
            addMessage('assistant', response.data.message)
            break
          }
          default:
            addMessage('assistant', UNKNOWN_COMMAND_MESSAGE)
        }
      } catch (error) {
        addMessage('assistant', 'Admin request failed.')
        setCanvas('auth-error', { message: error.message || 'Admin request failed.' })
      } finally {
        setChatBusy(false)
      }
    },
    async refreshStatus() {
      if (!this.state.auth.isAuthenticated) {
        return
      }
      setFooterLoading(true)
      setFooterError(null)
      try {
        const response = await statusApi.get(this.statusEtag)
        if (response.notModified) {
          return
        }
        this.statusEtag = response.etag
        const data = response.data || {}
        const sessionTokens =
          Number.isFinite(data.session_tokens) && data.session_tokens >= 0
            ? data.session_tokens
            : 0 // TODO: Replace with per-session tokens when backend exposes it.
        setFooterStatus({
          sessionTokens,
          reserveBalance: data.reserve_balance_dollars,
          updatedAt: data.updated_at,
          isLowBalance: data.is_low_balance,
        })
        if (this.state.canvas.type === 'dashboard' && this.state.auth.user) {
          setCanvas('dashboard', {
            user: this.state.auth.user,
            sessionTokens,
            reserveBalance: data.reserve_balance_dollars,
          })
        }
      } catch (error) {
        if (error.status === 401) {
          clearAuth()
          this.stopStatusPolling()
          this.promptLogin()
          return
        }
        setFooterError(error.message || 'Unable to refresh status.')
      } finally {
        setFooterLoading(false)
      }
    },
    startStatusPolling() {
      if (this.statusTimer) {
        return
      }
      this.statusTimer = setInterval(() => {
        this.refreshStatus()
      }, STATUS_REFRESH_MS)
    },
    stopStatusPolling() {
      if (this.statusTimer) {
        clearInterval(this.statusTimer)
        this.statusTimer = null
      }
    },
    deriveEmail(username) {
      if (username.includes('@')) {
        return username
      }
      return `${username}@afterresume.local`
    },
    buildUserUpdatePayload(params) {
      const payload = {}
      if (params.is_active !== undefined) {
        payload.is_active = params.is_active === 'true' || params.is_active === true
      }
      if (params.disable_reason) {
        payload.disable_reason = params.disable_reason
      }
      if (params.stripe_customer_id) {
        payload.stripe_customer_id = params.stripe_customer_id
      }
      if (params.notes) {
        payload.notes = params.notes
      }
      if (params.settings) {
        try {
          payload.settings = JSON.parse(params.settings)
        } catch {
          payload.settings = params.settings
        }
      }
      return payload
    },
  },
  errorCaptured(error) {
    addMessage('assistant', 'Something went wrong. Please try again.')
    setCanvas('auth-error', { message: error.message || 'Unexpected error.' })
    return false
  },
}
</script>
