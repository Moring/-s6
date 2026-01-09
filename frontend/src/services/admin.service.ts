import apiClient, { handleApiError } from './api'

export interface AdminUser {
  id: number
  username: string
  email: string
  is_active: boolean
  is_staff: boolean
  tenant_id?: number
  stripe_customer_id?: string
  settings?: any
  notes?: string
}

export interface AdminPasskey {
  id: number
  key: string
  expires_at: string
  used_at?: string
  used_by?: number
  created_by: number
  tenant_scope?: number
  max_uses: number
  uses_count: number
  is_active: boolean
}

export interface AuditEvent {
  id: number
  event_type: string
  user_id?: number
  tenant_id?: number
  timestamp: string
  metadata?: any
}

export interface FailedJob {
  id: string
  status: string
  error: string
  created_at: string
  updated_at: string
}

export interface RateLimitStats {
  limiter: string
  identifier: string
  count: number
  limit: number
  reset_at: string
}

export interface SystemControls {
  maintenance_mode: boolean
  disable_sharing: boolean
  feature_flags: {
    sharing: boolean
    exports: boolean
    ai_workflows: boolean
    email_notifications: boolean
    stripe: boolean
  }
  rate_limiting_enabled: boolean
  service_health: any
}

class AdminService {
  /**
   * List all users (admin only)
   */
  async listUsers(params?: { search?: string; is_active?: boolean }): Promise<{ results: AdminUser[] }> {
    try {
      const response = await apiClient.get('/api/admin/users/', { params })
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  /**
   * Update user (admin only)
   */
  async updateUser(userId: number, data: Partial<AdminUser>): Promise<AdminUser> {
    try {
      const response = await apiClient.patch(`/api/admin/users/${userId}/`, data)
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  /**
   * Reset user password (admin only)
   */
  async resetUserPassword(userId: number, newPassword: string): Promise<void> {
    try {
      await apiClient.post(`/api/admin/users/${userId}/reset-password/`, { new_password: newPassword })
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  /**
   * Create invite passkey (admin only)
   */
  async createPasskey(data: {
    expires_at: string
    tenant_scope?: number
    max_uses?: number
    notes?: string
  }): Promise<AdminPasskey> {
    try {
      const response = await apiClient.post('/api/admin/passkeys/', data)
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  /**
   * List passkeys (admin only)
   */
  async listPasskeys(params?: { active_only?: boolean; tenant_scope?: number }): Promise<{ results: AdminPasskey[] }> {
    try {
      const response = await apiClient.get('/api/admin/passkeys/list/', { params })
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  /**
   * List audit events (admin only)
   */
  async listAuditEvents(params?: {
    user_id?: number
    event_type?: string
    limit?: number
  }): Promise<{ results: AuditEvent[] }> {
    try {
      const response = await apiClient.get('/api/admin/audit-events/', { params })
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  /**
   * List failed jobs (admin only)
   */
  async listFailedJobs(limit?: number): Promise<{ results: FailedJob[] }> {
    try {
      const response = await apiClient.get('/api/admin/failed-jobs/', { params: { limit } })
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  /**
   * Retry failed job (admin only)
   */
  async retryFailedJob(jobId: string): Promise<void> {
    try {
      await apiClient.post(`/api/admin/failed-jobs/${jobId}/retry/`)
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  /**
   * Get rate limiting statistics (admin only)
   */
  async getRateLimitStats(): Promise<RateLimitStats[]> {
    try {
      const response = await apiClient.get('/api/admin/rate-limits/')
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  /**
   * Reset rate limit for identifier (admin only)
   */
  async resetRateLimit(limiter: string, identifier: string): Promise<void> {
    try {
      await apiClient.post('/api/admin/rate-limits/reset/', { limiter, identifier })
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  /**
   * Get system controls and feature flags (admin only)
   */
  async getSystemControls(): Promise<SystemControls> {
    try {
      const response = await apiClient.get('/api/admin/system-controls/')
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  /**
   * Toggle feature flag (admin only)
   */
  async toggleFeatureFlag(flag: string, enabled: boolean, ttl?: number): Promise<void> {
    try {
      await apiClient.post('/api/admin/system-controls/feature-flag/', { flag, enabled, ttl })
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  /**
   * Get gamification metrics (admin only)
   */
  async getGamificationMetrics(): Promise<any> {
    try {
      const response = await apiClient.get('/api/admin/gamification/metrics/')
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  /**
   * Grant XP manually (admin only)
   */
  async grantXP(userId: number, amount: number, reason: string): Promise<void> {
    try {
      await apiClient.post('/api/admin/gamification/grant/', { user_id: userId, amount, reason })
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  /**
   * Revoke badge manually (admin only)
   */
  async revokeBadge(userId: number, badgeId: number, reason: string): Promise<void> {
    try {
      await apiClient.post('/api/admin/gamification/revoke/', { user_id: userId, badge_id: badgeId, reason })
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }
}

export const adminService = new AdminService()
export default adminService
