import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import authService, { type User, type LoginRequest, type SignupRequest } from '@/services/auth.service'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Computed
  const isAuthenticated = computed(() => !!user.value)
  const isAdmin = computed(() => user.value?.is_staff || user.value?.is_superuser || false)
  const tenantId = computed(() => user.value?.tenant_id)

  // Actions
  async function login(credentials: LoginRequest) {
    loading.value = true
    error.value = null
    
    try {
      const response = await authService.login(credentials)
      user.value = response.user
      return response
    } catch (err: any) {
      error.value = err.message || 'Login failed'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function signup(data: SignupRequest) {
    loading.value = true
    error.value = null
    
    try {
      const response = await authService.signup(data)
      user.value = response.user
      return response
    } catch (err: any) {
      error.value = err.message || 'Signup failed'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function logout() {
    loading.value = true
    error.value = null
    
    try {
      await authService.logout()
      user.value = null
    } catch (err: any) {
      error.value = err.message || 'Logout failed'
      // Clear user anyway
      user.value = null
    } finally {
      loading.value = false
    }
  }

  async function fetchCurrentUser() {
    loading.value = true
    error.value = null
    
    try {
      const userData = await authService.me()
      user.value = userData
      return userData
    } catch (err: any) {
      error.value = err.message || 'Failed to fetch user'
      user.value = null
      throw err
    } finally {
      loading.value = false
    }
  }

  function initializeAuth() {
    // Try to load user from localStorage
    const storedUser = authService.getCurrentUser()
    if (storedUser && authService.isAuthenticated()) {
      user.value = storedUser
      // Optionally refresh user data from server
      fetchCurrentUser().catch(() => {
        // If fetch fails, clear user
        user.value = null
      })
    }
  }

  function clearError() {
    error.value = null
  }

  return {
    user,
    loading,
    error,
    isAuthenticated,
    isAdmin,
    tenantId,
    login,
    signup,
    logout,
    fetchCurrentUser,
    initializeAuth,
    clearError
  }
})
