import apiClient, { handleApiError } from './api'

export type ReportKind = 'resume' | 'status' | 'standup' | 'summary'

export interface Report {
  id: number
  user?: number
  kind: ReportKind
  content: any
  rendered_text: string
  rendered_html: string
  metadata?: any
  created_at: string
  updated_at: string
}

export interface ReportListResponse {
  count: number
  next: string | null
  previous: string | null
  results: Report[]
}

export interface GenerateReportRequest {
  kind: ReportKind
  start_date?: string
  end_date?: string
  format?: string
  options?: any
}

export interface ReportFilter {
  page?: number
  kind?: ReportKind
  date_from?: string
  date_to?: string
}

class ReportService {
  /**
   * List reports with optional filters
   */
  async list(filters?: ReportFilter): Promise<ReportListResponse> {
    try {
      const response = await apiClient.get<ReportListResponse>('/api/reports/', {
        params: filters
      })
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  /**
   * Generate a new report (async job)
   */
  async generate(request: GenerateReportRequest): Promise<{ job_id: string }> {
    try {
      const response = await apiClient.post<{ job_id: string }>('/api/reports/generate/', request)
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  /**
   * Refresh resume (async job)
   */
  async refreshResume(): Promise<{ job_id: string }> {
    try {
      const response = await apiClient.post<{ job_id: string }>('/api/resume/refresh/')
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  /**
   * List reports (alias for consistency)
   */
  async listReports(params?: any): Promise<ReportListResponse> {
    return this.list(params)
  }

  /**
   * Generate report (alias for consistency)
   */
  async generateReport(request: GenerateReportRequest): Promise<{ job_id: string }> {
    return this.generate(request)
  }

  /**
   * Delete a report
   */
  async deleteReport(reportId: number): Promise<void> {
    try {
      await apiClient.delete(`/api/reports/${reportId}/`)
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }
}

export const reportService = new ReportService()
export default reportService
