import apiClient, { handleApiError } from './api'

export interface BillingProfile {
  tenant_id: number
  stripe_customer_id?: string
  plan_tier?: string
  portal_flags?: any
}

export interface ReserveBalance {
  balance_cents: number
  balance_dollars: number
  currency: string
  updated_at: string
}

export interface ReserveLedgerEntry {
  id: number
  type: string
  amount_cents: number
  amount_dollars: number
  created_at: string
  related_job_id?: string
  related_stripe_event_id?: string
  notes?: string
}

export interface TopUpRequest {
  amount_cents: number
}

export interface CheckoutSession {
  checkout_url: string
  session_id: string
}

export interface PortalSession {
  portal_url: string
}

class BillingService {
  /**
   * Get billing profile
   */
  async getProfile(): Promise<BillingProfile> {
    try {
      const response = await apiClient.get<BillingProfile>('/api/billing/profile/')
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  /**
   * Get reserve balance
   */
  async getBalance(): Promise<ReserveBalance> {
    try {
      const response = await apiClient.get<ReserveBalance>('/api/billing/reserve/balance/')
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  /**
   * Get reserve ledger
   */
  async getLedger(limit?: number, offset?: number): Promise<ReserveLedgerEntry[]> {
    try {
      const response = await apiClient.get<ReserveLedgerEntry[]>('/api/billing/reserve/ledger/', {
        params: { limit, offset }
      })
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  /**
   * Create top-up checkout session
   */
  async createTopUpSession(request: TopUpRequest): Promise<CheckoutSession> {
    try {
      const response = await apiClient.post<CheckoutSession>('/api/billing/topup/session/', request)
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  /**
   * Create customer portal session
   */
  async createPortalSession(): Promise<PortalSession> {
    try {
      const response = await apiClient.post<PortalSession>('/api/billing/portal/session/')
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }

  /**
   * Aliases for consistency
   */
  async getBillingProfile(): Promise<BillingProfile> {
    return this.getProfile()
  }

  async getReserveBalance(): Promise<any> {
    return this.getBalance()
  }

  async getReserveLedger(params?: any): Promise<any> {
    return this.getLedger(params?.limit, params?.offset)
  }

  async exportLedger(): Promise<string> {
    try {
      const response = await apiClient.get('/api/billing/admin/ledger/export.csv', {
        responseType: 'text'
      })
      return response.data
    } catch (error) {
      throw new Error(handleApiError(error))
    }
  }
}

export const billingService = new BillingService()
export default billingService
