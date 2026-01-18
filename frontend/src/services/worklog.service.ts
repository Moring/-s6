import apiClient, { handleApiError } from './api'

export interface Client {
  id: number
  name: string
  description?: string
  is_active: boolean
  website?: string
  notes?: string
  created_at: string
  updated_at: string
}

export interface Project {
  id: number
  client: number
  client_name?: string
  name: string
  description?: string
  is_active: boolean
  role?: string
  started_on?: string
  ended_on?: string
  created_at: string
  updated_at: string
}

export interface Epic {
  id: number
  project: number
  project_name?: string
  name: string
  description?: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface Feature {
  id: number
  epic: number
  epic_name?: string
  name: string
  description?: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface Story {
  id: number
  feature: number
  feature_name?: string
  name: string
  description?: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface Task {
  id: number
  story: number
  story_name?: string
  name: string
  description?: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface Sprint {
  id: number
  project: number
  project_name?: string
  name: string
  goal?: string
  start_date?: string
  end_date?: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export type WorkType = 'delivery' | 'planning' | 'incident' | 'support' | 'learning' | 'other'
export type WorkLogStatus = 'draft' | 'ready' | 'final' | 'archived'
export type EnrichmentStatus = 'pending' | 'enriched' | 'reviewed' | 'rejected' | 'error'
export type WorkSource = 'manual' | 'assistant' | 'email' | 'slack' | 'calendar' | 'ticket' | 'other'

export interface WorkLog {
  id?: number
  user?: number
  
  // Date field (occurred_on in backend)
  occurred_on: string
  
  // Optional title
  title?: string
  
  // Organizational hierarchy (all optional)
  client?: number | null
  client_name?: string | null
  project?: number | null
  project_name?: string | null
  epic?: number | null
  epic_name?: string | null
  feature?: number | null
  feature_name?: string | null
  story?: number | null
  story_name?: string | null
  task?: number | null
  task_name?: string | null
  sprint?: number | null
  sprint_name?: string | null
  
  // Core content
  content: string
  outcome?: string
  impact?: string
  next_steps?: string
  
  work_type: WorkType
  status: WorkLogStatus
  
  // Time tracking (optional, in minutes)
  effort_minutes?: number | null
  hours?: number | null  // Computed property
  is_billable?: boolean
  
  // Tags and skills
  tags?: string[]
  
  // Source and enrichment
  source: WorkSource
  source_ref?: string
  metadata?: any
  enrichment_status: EnrichmentStatus
  enrichment_suggestions?: any
  
  // AI summary
  ai_summary?: string
  
  created_at?: string
  updated_at?: string
  attachments?: Attachment[]
  attachment_count?: number
  skill_signals?: SkillSignal[]
  bullets?: Bullet[]
  external_links?: ExternalLink[]
}

export type AttachmentKind = 'image' | 'document' | 'code' | 'audio' | 'video' | 'other'
export type StorageProvider = 'minio' | 'local' | 'other'

export interface Attachment {
  id: number
  worklog: number
  uploaded_by?: number
  kind: AttachmentKind
  storage_provider: StorageProvider
  object_key: string
  filename: string
  mime_type?: string
  description?: string
  size_bytes: number
  checksum_sha256?: string
  metadata?: any
  created_at: string
}

export type SignalStatus = 'suggested' | 'accepted' | 'rejected'
export type SignalSource = 'ai' | 'manual' | 'import'
export type SkillKind = 'skill' | 'technology' | 'tool' | 'method' | 'domain'

export interface SkillSignal {
  id: number
  worklog: number
  name: string
  kind: SkillKind
  confidence: number
  source: SignalSource
  status: SignalStatus
  evidence?: string
  metadata?: any
  created_at: string
}

export type BulletKind = 'note' | 'status' | 'resume'

export interface Bullet {
  id: number
  worklog: number
  kind: BulletKind
  text: string
  is_ai_generated: boolean
  is_selected: boolean
  order: number
  metrics?: any
  metadata?: any
  created_at: string
}

export type ExternalSystem = 'jira' | 'github' | 'gitlab' | 'linear' | 'asana' | 'other'

export interface ExternalLink {
  id: number
  worklog: number
  system: ExternalSystem
  key?: string
  url: string
  title?: string
  metadata?: any
  created_at: string
}

export interface WorkLogPreset {
  id: number
  user: number
  name: string
  description?: string
  client?: number | null
  project?: number | null
  default_work_type: WorkType
  default_tags?: string[]
  intake_prompt?: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export type ReportKind = 'weekly' | 'monthly' | 'sprint' | 'custom'
export type CreatedVia = 'manual' | 'assistant' | 'scheduled'

export interface WorkLogReport {
  id: number
  user: number
  client?: number | null
  project?: number | null
  sprint?: number | null
  kind: ReportKind
  created_via: CreatedVia
  period_start?: string
  period_end?: string
  title?: string
  content_md: string
  metadata?: any
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
  limit?: number
  search?: string
  start_date?: string
  end_date?: string
  client?: number
  project?: number
  epic?: number
  feature?: number
  story?: number
  task?: number
  sprint?: number
  work_type?: WorkType
  status?: WorkLogStatus
  enrichment_status?: EnrichmentStatus
  ordering?: string
}

class WorkLogService {
  // ===== Client Management =====
  
  async listClients(): Promise<Client[]> {
    try {
      const response = await apiClient.get<Client[]>('/api/clients/')
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  async getClient(id: number): Promise<Client> {
    try {
      const response = await apiClient.get<Client>(`/api/clients/${id}/`)
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  async createClient(data: Partial<Client>): Promise<Client> {
    try {
      const response = await apiClient.post<Client>('/api/clients/', data)
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  async updateClient(id: number, data: Partial<Client>): Promise<Client> {
    try {
      const response = await apiClient.patch<Client>(`/api/clients/${id}/`, data)
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  async deleteClient(id: number): Promise<void> {
    try {
      await apiClient.delete(`/api/clients/${id}/`)
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  // ===== Project Management =====
  
  async listProjects(clientId?: number): Promise<Project[]> {
    try {
      const params = clientId ? { client: clientId } : {}
      const response = await apiClient.get<Project[]>('/api/projects/', { params })
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  async getProject(id: number): Promise<Project> {
    try {
      const response = await apiClient.get<Project>(`/api/projects/${id}/`)
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  async createProject(data: Partial<Project>): Promise<Project> {
    try {
      const response = await apiClient.post<Project>('/api/projects/', data)
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  async updateProject(id: number, data: Partial<Project>): Promise<Project> {
    try {
      const response = await apiClient.patch<Project>(`/api/projects/${id}/`, data)
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  async deleteProject(id: number): Promise<void> {
    try {
      await apiClient.delete(`/api/projects/${id}/`)
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  // ===== Epic Management =====
  
  async listEpics(projectId?: number): Promise<Epic[]> {
    try {
      const params = projectId ? { project: projectId } : {}
      const response = await apiClient.get<Epic[]>('/api/epics/', { params })
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  async createEpic(data: Partial<Epic>): Promise<Epic> {
    try {
      const response = await apiClient.post<Epic>('/api/epics/', data)
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  // ===== Feature Management =====
  
  async listFeatures(epicId?: number): Promise<Feature[]> {
    try {
      const params = epicId ? { epic: epicId } : {}
      const response = await apiClient.get<Feature[]>('/api/features/', { params })
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  async createFeature(data: Partial<Feature>): Promise<Feature> {
    try {
      const response = await apiClient.post<Feature>('/api/features/', data)
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  // ===== Story Management =====
  
  async listStories(featureId?: number): Promise<Story[]> {
    try {
      const params = featureId ? { feature: featureId } : {}
      const response = await apiClient.get<Story[]>('/api/stories/', { params })
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  async createStory(data: Partial<Story>): Promise<Story> {
    try {
      const response = await apiClient.post<Story>('/api/stories/', data)
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  // ===== Task Management =====
  
  async listTasks(storyId?: number): Promise<Task[]> {
    try {
      const params = storyId ? { story: storyId } : {}
      const response = await apiClient.get<Task[]>('/api/tasks/', { params })
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  async createTask(data: Partial<Task>): Promise<Task> {
    try {
      const response = await apiClient.post<Task>('/api/tasks/', data)
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  // ===== Sprint Management =====
  
  async listSprints(projectId?: number): Promise<Sprint[]> {
    try {
      const params = projectId ? { project: projectId } : {}
      const response = await apiClient.get<Sprint[]>('/api/sprints/', { params })
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  async createSprint(data: Partial<Sprint>): Promise<Sprint> {
    try {
      const response = await apiClient.post<Sprint>('/api/sprints/', data)
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  // ===== Worklog Management =====
  
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
  async create(data: Partial<WorkLog>): Promise<WorkLog> {
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

  // ===== Attachment Management =====
  
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

  // ===== Skill Signals Management =====
  
  async listSkillSignals(worklogId: number): Promise<SkillSignal[]> {
    try {
      const response = await apiClient.get<SkillSignal[]>(`/api/worklogs/${worklogId}/skill-signals/`)
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  async updateSkillSignal(worklogId: number, signalId: number, data: Partial<SkillSignal>): Promise<SkillSignal> {
    try {
      const response = await apiClient.patch<SkillSignal>(`/api/worklogs/${worklogId}/skill-signals/${signalId}/`, data)
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  async acceptSkillSignal(worklogId: number, signalId: number): Promise<SkillSignal> {
    return this.updateSkillSignal(worklogId, signalId, { status: 'accepted' })
  }

  async rejectSkillSignal(worklogId: number, signalId: number): Promise<SkillSignal> {
    return this.updateSkillSignal(worklogId, signalId, { status: 'rejected' })
  }

  // ===== Bullets Management =====
  
  async listBullets(worklogId: number): Promise<Bullet[]> {
    try {
      const response = await apiClient.get<Bullet[]>(`/api/worklogs/${worklogId}/bullets/`)
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  async updateBullet(worklogId: number, bulletId: number, data: Partial<Bullet>): Promise<Bullet> {
    try {
      const response = await apiClient.patch<Bullet>(`/api/worklogs/${worklogId}/bullets/${bulletId}/`, data)
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  // ===== External Links Management =====
  
  async listExternalLinks(worklogId: number): Promise<ExternalLink[]> {
    try {
      const response = await apiClient.get<ExternalLink[]>(`/api/worklogs/${worklogId}/external-links/`)
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  async createExternalLink(worklogId: number, data: Partial<ExternalLink>): Promise<ExternalLink> {
    try {
      const response = await apiClient.post<ExternalLink>(`/api/worklogs/${worklogId}/external-links/`, data)
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  async deleteExternalLink(worklogId: number, linkId: number): Promise<void> {
    try {
      await apiClient.delete(`/api/worklogs/${worklogId}/external-links/${linkId}/`)
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  // ===== Presets Management =====
  
  async listPresets(): Promise<WorkLogPreset[]> {
    try {
      const response = await apiClient.get<WorkLogPreset[]>('/api/worklog-presets/')
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  async createPreset(data: Partial<WorkLogPreset>): Promise<WorkLogPreset> {
    try {
      const response = await apiClient.post<WorkLogPreset>('/api/worklog-presets/', data)
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  // ===== Reports Management =====
  
  async listReports(): Promise<WorkLogReport[]> {
    try {
      const response = await apiClient.get<WorkLogReport[]>('/api/worklog-reports/')
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  async getReport(id: number): Promise<WorkLogReport> {
    try {
      const response = await apiClient.get<WorkLogReport>(`/api/worklog-reports/${id}/`)
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  async generateReport(data: {
    kind: ReportKind
    client?: number
    project?: number
    sprint?: number
    period_start?: string
    period_end?: string
  }): Promise<{ job_id: string }> {
    try {
      const response = await apiClient.post<{ job_id: string }>('/api/worklogs/reports/generate/', data)
      return response.data
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

  async createWorklog(data: Partial<WorkLog>): Promise<WorkLog> {
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
