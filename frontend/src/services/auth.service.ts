import apiClient, { handleApiError } from './api'

export interface LoginRequest {
  username: string
  password: string
}

export interface SignupRequest {
  username: string
  email: string
  password: string
  passkey: string
}

export interface LoginResponse {
  access: string
  refresh: string
  user: User
}

export interface User {
  id: number
  username: string
  email: string
  tenant_id: number
  tenant_name?: string
  is_staff?: boolean
  is_superuser?: boolean
  profile?: UserProfile
}

export interface UserProfile {
  stripe_customer_id?: string
  settings?: any
  notes?: string
}

export interface PasswordChangeRequest {
  old_password: string
  new_password: string
}

export interface PasswordResetRequest {
  email: string
}

class AuthService {
  /**
   * Login with username and password
   */
  async login(credentials: LoginRequest): Promise<LoginResponse> {
    try {
      const response = await apiClient.post<LoginResponse>('/api/auth/login/', credentials)
      
      // Store tokens and user info
      if (response.data.access) {
        localStorage.setItem('access_token', response.data.access)
      }
      if (response.data.user) {
        localStorage.setItem('user', JSON.stringify(response.data.user))
      }
      
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  /**
   * Signup with invite passkey
   */
  async signup(data: SignupRequest): Promise<LoginResponse> {
    try {
      const response = await apiClient.post<LoginResponse>('/api/auth/signup/', data)
      
      // Store tokens and user info
      if (response.data.access) {
        localStorage.setItem('access_token', response.data.access)
      }
      if (response.data.user) {
        localStorage.setItem('user', JSON.stringify(response.data.user))
      }
      
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  /**
   * Logout current user
   */
  async logout(): Promise<void> {
    try {
      await apiClient.post('/api/auth/logout/')
    } catch (error) {
      // Ignore logout errors
      console.error('Logout error:', error)
    } finally {
      // Always clear local storage
      localStorage.removeItem('access_token')
      localStorage.removeItem('user')
    }
  }

  /**
   * Get current user information
   */
  async me(): Promise<User> {
    try {
      const response = await apiClient.get<User>('/api/me/')
      localStorage.setItem('user', JSON.stringify(response.data))
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  /**
   * Change password
   */
  async changePassword(data: PasswordChangeRequest): Promise<void> {
    try {
      await apiClient.post('/api/auth/password/change/', data)
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  /**
   * Request password reset
   */
  async resetPassword(data: PasswordResetRequest): Promise<void> {
    try {
      await apiClient.post('/api/auth/password/reset/', data)
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  /**
   * Check if user is authenticated
   */
  isAuthenticated(): boolean {
    return !!localStorage.getItem('access_token')
  }

  /**
   * Get stored user information
   */
  getCurrentUser(): User | null {
    const userStr = localStorage.getItem('user')
    if (userStr) {
      try {
        return JSON.parse(userStr)
      } catch {
        return null
      }
    }
    return null
  }

  /**
   * Check if current user is admin
   */
  isAdmin(): boolean {
    const user = this.getCurrentUser()
    return user?.is_staff || user?.is_superuser || false
  }
}

export default new AuthService()
