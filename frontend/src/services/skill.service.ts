import apiClient, { handleApiError } from './api'

export interface Skill {
  id: number
  user?: number
  name: string
  normalized: string
  confidence: number
  level?: string | null
  metadata?: any
  created_at: string
  updated_at: string
  evidence_count: number
}

export interface SkillEvidence {
  id: number
  source_type: string
  source_id: number
  excerpt: string
  weight: number
  created_at: string
}

export interface SkillListResponse {
  count: number
  next: string | null
  previous: string | null
  results: Skill[]
}

export interface SkillEvidenceListResponse {
  count: number
  next: string | null
  previous: string | null
  results: SkillEvidence[]
}

export interface SkillFilter {
  page?: number
  search?: string
  category?: string
  confidence_min?: number
}

class SkillService {
  /**
   * List skills with optional filters
   */
  async list(filters?: SkillFilter): Promise<SkillListResponse> {
    try {
      const response = await apiClient.get<SkillListResponse>('/api/skills/', {
        params: filters
      })
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  /**
   * Get skill evidence
   */
  async getEvidence(skillId: number, page?: number): Promise<SkillEvidenceListResponse> {
    try {
      const response = await apiClient.get<SkillEvidenceListResponse>(
        `/api/skills/${skillId}/evidence/`,
        {
          params: { page }
        }
      )
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  /**
   * Trigger skills recomputation job
   */
  async recompute(): Promise<{ job_id: string }> {
    try {
      const response = await apiClient.post<{ job_id: string }>('/api/skills/recompute/')
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  /**
   * List skills (alias for consistency)
   */
  async listSkills(params?: any): Promise<SkillListResponse> {
    return this.list(params)
  }

  /**
   * Get skill evidence (alias for consistency)
   */
  async getSkillEvidence(skillId: number, page?: number): Promise<SkillEvidenceListResponse> {
    return this.getEvidence(skillId, page)
  }

  /**
   * Recompute skills (alias for consistency)
   */
  async recomputeSkills(): Promise<{ job_id: string }> {
    return this.recompute()
  }

  /**
   * Export skills
   */
  async exportSkills(format: 'csv' | 'json'): Promise<string> {
    try {
      const response = await apiClient.get(`/api/skills/export.${format}`, {
        responseType: 'text'
      })
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }
}

export const skillService = new SkillService()
export default skillService
