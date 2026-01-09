import apiClient, { handleApiError } from './api'

export interface Artifact {
  id: number
  kind: string
  filename: string
  size_bytes: number
  created_at: string
  download_url?: string
}

export interface ArtifactListResponse {
  results: Artifact[]
  count: number
  next: string | null
  previous: string | null
}

class ArtifactService {
  /**
   * List all artifacts
   */
  async listArtifacts(params?: {
    page?: number
    limit?: number
    kind?: string
    search?: string
  }): Promise<ArtifactListResponse> {
    try {
      const response = await apiClient.get<ArtifactListResponse>('/api/artifacts/', {
        params,
      })
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  /**
   * Upload a file
   */
  async uploadFile(file: File, kind: string = 'document'): Promise<Artifact> {
    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('kind', kind)

      const response = await apiClient.post<Artifact>('/api/artifacts/upload/', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      })
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  /**
   * Upload multiple files
   */
  async uploadFiles(files: File[], kind: string = 'document'): Promise<Artifact[]> {
    try {
      const uploadPromises = files.map((file) => this.uploadFile(file, kind))
      return await Promise.all(uploadPromises)
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  /**
   * Download a file (returns blob URL)
   */
  async downloadFile(artifactId: number): Promise<string> {
    try {
      const response = await apiClient.get(`/api/artifacts/${artifactId}/download/`, {
        responseType: 'blob',
      })
      return URL.createObjectURL(response.data)
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  /**
   * Delete an artifact
   */
  async deleteArtifact(artifactId: number): Promise<void> {
    try {
      await apiClient.delete(`/api/artifacts/${artifactId}/`)
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }
}

export const artifactService = new ArtifactService()
export default artifactService
