import apiClient, { handleApiError } from './api'

export interface Sprint {
  id?: number
  project: number
  project_name?: string
  name: string
  goal?: string
  start_date?: string | null
  end_date?: string | null
  is_active?: boolean
  created_at?: string
  updated_at?: string
}

export interface SprintListResponse {
  count: number
  next: string | null
  previous: string | null
  results: Sprint[]
}

export interface SprintFilter {
  page?: number
  project?: number
  is_active?: boolean
  ordering?: string
}

class SprintService {
  /**
   * List sprints with optional filters
   */
  async list(filters?: SprintFilter): Promise<SprintListResponse> {
    try {
      const response = await apiClient.get<SprintListResponse>('/api/sprints/', {
        params: filters
      })
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  /**
   * Get a single sprint by ID
   */
  async get(id: number): Promise<Sprint> {
    try {
      const response = await apiClient.get<Sprint>(`/api/sprints/${id}/`)
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  /**
   * Create a new sprint
   */
  async create(data: Sprint): Promise<Sprint> {
    try {
      const response = await apiClient.post<Sprint>('/api/sprints/', data)
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  /**
   * Update an existing sprint
   */
  async update(id: number, data: Partial<Sprint>): Promise<Sprint> {
    try {
      const response = await apiClient.patch<Sprint>(`/api/sprints/${id}/`, data)
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  /**
   * Delete a sprint
   */
  async delete(id: number): Promise<void> {
    try {
      await apiClient.delete(`/api/sprints/${id}/`)
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  /**
   * Get sprints for a specific project
   */
  async getByProject(projectId: number): Promise<Sprint[]> {
    try {
      const response = await this.list({ project: projectId, is_active: true })
      return response.results
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  /**
   * Get active sprints
   */
  async getActive(): Promise<Sprint[]> {
    try {
      const response = await this.list({ is_active: true })
      return response.results
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }
}

export const sprintService = new SprintService()
export default sprintService
