import apiClient, { handleApiError } from './api'

export interface Client {
  id?: number
  name: string
  description?: string
  is_active?: boolean
  created_at?: string
  updated_at?: string
}

export interface ClientListResponse {
  count: number
  next: string | null
  previous: string | null
  results: Client[]
}

export interface ClientFilter {
  page?: number
  search?: string
  is_active?: boolean
  ordering?: string
}

class ClientService {
  /**
   * List clients with optional filters
   */
  async list(filters?: ClientFilter): Promise<ClientListResponse> {
    try {
      const response = await apiClient.get<ClientListResponse>('/api/clients/', {
        params: filters
      })
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  /**
   * Get a single client by ID
   */
  async get(id: number): Promise<Client> {
    try {
      const response = await apiClient.get<Client>(`/api/clients/${id}/`)
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  /**
   * Create a new client
   */
  async create(data: Client): Promise<Client> {
    try {
      const response = await apiClient.post<Client>('/api/clients/', data)
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  /**
   * Update an existing client
   */
  async update(id: number, data: Partial<Client>): Promise<Client> {
    try {
      const response = await apiClient.patch<Client>(`/api/clients/${id}/`, data)
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  /**
   * Delete a client
   */
  async delete(id: number): Promise<void> {
    try {
      await apiClient.delete(`/api/clients/${id}/`)
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  /**
   * Get all active clients (helper for dropdowns)
   */
  async getActive(): Promise<Client[]> {
    try {
      const response = await this.list({ is_active: true })
      return response.results
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }
}

export const clientService = new ClientService()
export default clientService
