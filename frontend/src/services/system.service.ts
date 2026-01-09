import apiClient, { handleApiError } from './api'

export interface JobStatus {
  id: string
  status: 'queued' | 'running' | 'success' | 'failed'
  created_at: string
  updated_at: string
  result?: any
  error?: string
}

export interface JobEvent {
  id: number
  event_type: string
  timestamp: string
  metadata?: any
}

export interface StatusBarData {
  reserve_balance_cents: number
  reserve_balance_dollars: number
  tokens_in: number
  tokens_out: number
  jobs_running: number
  updated_at: string
}

class SystemService {
  /**
   * Get job status
   */
  async getJobStatus(jobId: string): Promise<JobStatus> {
    try {
      const response = await apiClient.get<JobStatus>(`/api/jobs/${jobId}/`)
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  /**
   * Get job events timeline
   */
  async getJobEvents(jobId: string): Promise<JobEvent[]> {
    try {
      const response = await apiClient.get<JobEvent[]>(`/api/jobs/${jobId}/events/`)
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  /**
   * Get status bar data
   */
  async getStatusBar(): Promise<StatusBarData> {
    try {
      const response = await apiClient.get<StatusBarData>('/api/status/bar/')
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  /**
   * Health check
   */
  async healthCheck(): Promise<{ status: string }> {
    try {
      const response = await apiClient.get<{ status: string }>('/api/healthz/')
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  /**
   * Readiness check
   */
  async readinessCheck(): Promise<{ status: string; services: any }> {
    try {
      const response = await apiClient.get<{ status: string; services: any }>('/api/readyz/')
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  /**
   * Get gamification summary for current user
   */
  async getGamificationSummary(): Promise<any> {
    try {
      const response = await apiClient.get('/api/gamification/summary/')
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  /**
   * Get readyz data (comprehensive health check)
   */
  async getReadyz(): Promise<any> {
    try {
      const response = await apiClient.get('/api/readyz/')
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }
}

export const systemService = new SystemService()
export default systemService
