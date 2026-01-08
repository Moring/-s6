import apiClient, { handleApiError } from './api'

export interface WorkLog {
  id?: number
  user?: number
  date: string
  content: string
  source?: string
  metadata?: any
  created_at?: string
  updated_at?: string
  attachments?: Attachment[]
}

export interface Attachment {
  id: number
  kind: string
  filename: string
  size_bytes: number
  created_at: string
}

export interface WorkLogListResponse {
  count: number
  next: string | null
  previous: string | null
  results: WorkLog[]
}

export interface WorkLogFilter {
  page?: number
  search?: string
  date_from?: string
  date_to?: string
  source?: string
}

class WorkLogService {
  /**
   * List worklogs with optional filters
   */
  async list(filters?: WorkLogFilter): Promise<WorkLogListResponse> {
    try {
      const response = await apiClient.get<WorkLogListResponse>('/api/worklogs/', {
        params: filters
      })
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  /**
   * Get a single worklog by ID
   */
  async get(id: number): Promise<WorkLog> {
    try {
      const response = await apiClient.get<WorkLog>(`/api/worklogs/${id}/`)
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  /**
   * Create a new worklog entry
   */
  async create(data: WorkLog): Promise<WorkLog> {
    try {
      const response = await apiClient.post<WorkLog>('/api/worklogs/', data)
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  /**
   * Update an existing worklog entry
   */
  async update(id: number, data: Partial<WorkLog>): Promise<WorkLog> {
    try {
      const response = await apiClient.patch<WorkLog>(`/api/worklogs/${id}/`, data)
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  /**
   * Delete a worklog entry
   */
  async delete(id: number): Promise<void> {
    try {
      await apiClient.delete(`/api/worklogs/${id}/`)
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  /**
   * Upload attachment to worklog
   */
  async uploadAttachment(worklogId: number, file: File, description?: string): Promise<Attachment> {
    try {
      const formData = new FormData()
      formData.append('file', file)
      if (description) {
        formData.append('description', description)
      }

      const response = await apiClient.post<Attachment>(
        `/api/worklogs/${worklogId}/attachments/`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        }
      )
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  /**
   * List attachments for a worklog
   */
  async listAttachments(worklogId: number): Promise<Attachment[]> {
    try {
      const response = await apiClient.get<Attachment[]>(`/api/worklogs/${worklogId}/attachments-list/`)
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  /**
   * Delete an attachment
   */
  async deleteAttachment(worklogId: number, attachmentId: number): Promise<void> {
    try {
      await apiClient.delete(`/api/worklogs/${worklogId}/attachments/${attachmentId}/`)
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  /**
   * Analyze worklog entry (trigger AI job)
   */
  async analyze(id: number): Promise<{ job_id: string }> {
    try {
      const response = await apiClient.post<{ job_id: string }>(`/api/worklogs/${id}/analyze/`)
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  /**
   * Aliases for consistency with other services
   */
  async listWorklogs(params?: any): Promise<WorkLogListResponse> {
    return this.list(params)
  }

  async getWorklog(id: number): Promise<WorkLog> {
    return this.get(id)
  }

  async createWorklog(data: WorkLog): Promise<WorkLog> {
    return this.create(data)
  }

  async updateWorklog(id: number, data: Partial<WorkLog>): Promise<WorkLog> {
    return this.update(id, data)
  }

  async deleteWorklog(id: number): Promise<void> {
    return this.delete(id)
  }
}

export const worklogService = new WorkLogService()
export default worklogService
