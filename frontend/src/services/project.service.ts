import apiClient, { handleApiError } from './api'

export interface Project {
  id?: number
  client: number
  client_name?: string
  name: string
  description?: string
  is_active?: boolean
  created_at?: string
  updated_at?: string
}

export interface ProjectListResponse {
  count: number
  next: string | null
  previous: string | null
  results: Project[]
}

export interface ProjectFilter {
  page?: number
  client?: number
  is_active?: boolean
  search?: string
  ordering?: string
}

class ProjectService {
  /**
   * List projects with optional filters
   */
  async list(filters?: ProjectFilter): Promise<ProjectListResponse> {
    try {
      const response = await apiClient.get<ProjectListResponse>('/api/projects/', {
        params: filters
      })
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  /**
   * Get a single project by ID
   */
  async get(id: number): Promise<Project> {
    try {
      const response = await apiClient.get<Project>(`/api/projects/${id}/`)
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  /**
   * Create a new project
   */
  async create(data: Project): Promise<Project> {
    try {
      const response = await apiClient.post<Project>('/api/projects/', data)
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  /**
   * Update an existing project
   */
  async update(id: number, data: Partial<Project>): Promise<Project> {
    try {
      const response = await apiClient.patch<Project>(`/api/projects/${id}/`, data)
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  /**
   * Delete a project
   */
  async delete(id: number): Promise<void> {
    try {
      await apiClient.delete(`/api/projects/${id}/`)
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  /**
   * Get projects for a specific client
   */
  async getByClient(clientId: number): Promise<Project[]> {
    try {
      const response = await this.list({ client: clientId, is_active: true })
      return response.results
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  /**
   * Get all active projects (helper for dropdowns)
   */
  async getActive(): Promise<Project[]> {
    try {
      const response = await this.list({ is_active: true })
      return response.results
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }
}

export const projectService = new ProjectService()
export default projectService
