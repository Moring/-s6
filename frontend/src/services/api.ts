import axios, { type AxiosInstance, type AxiosRequestConfig, type AxiosResponse } from 'axios'

// API base URL - will be configured via environment variable
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

// Create axios instance with default configuration
const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  },
  withCredentials: true // Important for cookie-based auth
})

// Request interceptor for adding auth token
apiClient.interceptors.request.use(
  (config) => {
    // Get JWT token from localStorage if exists
    const token = localStorage.getItem('access_token')
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor for handling token refresh
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    // If 401 and not already retried, try to refresh token
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      try {
        // Try to refresh the access token
        const response = await axios.post(
          `${API_BASE_URL}/api/auth/token/refresh/`,
          {},
          { withCredentials: true }
        )

        if (response.data.access) {
          localStorage.setItem('access_token', response.data.access)
          originalRequest.headers.Authorization = `Bearer ${response.data.access}`
          return apiClient(originalRequest)
        }
      } catch (refreshError) {
        // Refresh failed, redirect to login
        localStorage.removeItem('access_token')
        localStorage.removeItem('user')
        window.location.href = '/auth/login'
        return Promise.reject(refreshError)
      }
    }

    return Promise.reject(error)
  }
)

export default apiClient

// Helper function for handling API errors
export function handleApiError(error: any): string {
  if (error.response) {
    // The request was made and the server responded with a status code
    // that falls out of the range of 2xx
    if (error.response.data?.detail) {
      return error.response.data.detail
    }
    if (error.response.data?.error) {
      return error.response.data.error
    }
    if (typeof error.response.data === 'string') {
      return error.response.data
    }
    return `Server error: ${error.response.status}`
  } else if (error.request) {
    // The request was made but no response was received
    return 'No response from server. Please check your connection.'
  } else {
    // Something happened in setting up the request that triggered an Error
    return error.message || 'An unexpected error occurred'
  }
}
