<template>
    <MainLayout>
        <BContainer fluid>
            <PageBreadcrumb title="Billing" />

            <!-- Reserve Balance Card -->
            <BRow class="mb-3">
                <BCol lg="6" class="mb-3">
                    <UICard title="Reserve Balance">
                        <div class="text-center py-4">
                            <Icon icon="tabler:wallet" :width="64" :height="64" class="text-primary mb-3" />
                            <h2 class="mb-1">${{ reserveBalance.reserve_balance_dollars }}</h2>
                            <small class="text-muted">{{ reserveBalance.reserve_balance_cents }} cents available</small>
                            
                            <div class="mt-4">
                                <BButton variant="primary" @click="showTopUpModal = true">
                                    <Icon icon="tabler:plus" class="me-1" />
                                    Top Up Balance
                                </BButton>
                            </div>
                        </div>
                    </UICard>
                </BCol>

                <BCol lg="6" class="mb-3">
                    <UICard title="Billing Profile">
                        <div v-if="loadingProfile">
                            <div class="text-center py-4">
                                <div class="spinner-border text-primary" role="status">
                                    <span class="visually-hidden">Loading...</span>
                                </div>
                            </div>
                        </div>
                        <div v-else-if="billingProfile">
                            <div class="mb-3">
                                <label class="form-label text-muted small">Plan</label>
                                <div>
                                    <BBadge variant="primary" size="lg">{{ billingProfile.plan_tier || 'Free' }}</BBadge>
                                </div>
                            </div>
                            <div class="mb-3">
                                <label class="form-label text-muted small">Stripe Customer ID</label>
                                <div>{{ billingProfile.stripe_customer_id || 'Not set' }}</div>
                            </div>
                            <div class="mt-4">
                                <BButton variant="outline-primary" @click="openCustomerPortal" :disabled="openingPortal">
                                    <span v-if="openingPortal">
                                        <span class="spinner-border spinner-border-sm me-1"></span>
                                        Opening...
                                    </span>
                                    <span v-else>
                                        <Icon icon="tabler:settings" class="me-1" />
                                        Manage Billing
                                    </span>
                                </BButton>
                            </div>
                        </div>
                    </UICard>
                </BCol>
            </BRow>

            <!-- Ledger -->
            <BRow>
                <BCol cols="12">
                    <UICard title="Transaction History">
                        <template #actions>
                            <BButton variant="outline-secondary" size="sm" @click="exportLedger">
                                <Icon icon="tabler:download" class="me-1" />
                                Export CSV
                            </BButton>
                        </template>

                        <div v-if="loadingLedger" class="text-center py-5">
                            <div class="spinner-border text-primary" role="status">
                                <span class="visually-hidden">Loading...</span>
                            </div>
                        </div>

                        <div v-else-if="ledger.length === 0" class="text-center py-5 text-muted">
                            <Icon icon="tabler:receipt-off" :width="64" :height="64" class="mb-3" />
                            <h5>No transactions yet</h5>
                            <p>Your transaction history will appear here</p>
                        </div>

                        <div v-else>
                            <div class="table-responsive">
                                <table class="table table-hover">
                                    <thead>
                                        <tr>
                                            <th>Date</th>
                                            <th>Type</th>
                                            <th>Description</th>
                                            <th>Amount</th>
                                            <th>Balance</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <tr v-for="entry in ledger" :key="entry.id">
                                            <td>{{ formatDateTime(entry.created_at) }}</td>
                                            <td>
                                                <BBadge :variant="getEntryTypeBadge(entry.type)">
                                                    {{ entry.type }}
                                                </BBadge>
                                            </td>
                                            <td>{{ entry.notes || '-' }}</td>
                                            <td :class="entry.amount_cents > 0 ? 'text-success' : 'text-danger'">
                                                {{ entry.amount_cents > 0 ? '+' : '' }}${{ (entry.amount_cents / 100).toFixed(2) }}
                                            </td>
                                            <td>${{ (entry.balance_after / 100).toFixed(2) }}</td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>

                            <!-- Pagination -->
                            <div v-if="totalPages > 1" class="d-flex justify-content-between align-items-center mt-4">
                                <div class="text-muted">
                                    Showing {{ (currentPage - 1) * pageSize + 1 }} to {{ Math.min(currentPage * pageSize, totalItems) }} of {{ totalItems }} entries
                                </div>
                                <BPagination
                                    v-model="currentPage"
                                    :total-rows="totalItems"
                                    :per-page="pageSize"
                                    @update:model-value="fetchLedger"
                                />
                            </div>
                        </div>
                    </UICard>
                </BCol>
            </BRow>
        </BContainer>

        <!-- Top Up Modal -->
        <BModal
            v-model="showTopUpModal"
            title="Top Up Reserve Balance"
            @hidden="resetTopUpForm"
        >
            <BForm @submit.prevent="handleTopUp">
                <BFormGroup label="Amount (USD)" label-for="amount">
                    <BFormInput
                        id="amount"
                        v-model.number="topUpForm.amount"
                        type="number"
                        min="10"
                        max="1000"
                        step="10"
                        required
                        placeholder="Enter amount"
                    />
                    <small class="text-muted">Minimum: $10, Maximum: $1,000</small>
                </BFormGroup>

                <div class="alert alert-info">
                    <Icon icon="tabler:info-circle" class="me-1" />
                    You will be redirected to Stripe to complete the payment
                </div>
            </BForm>

            <template #footer>
                <BButton variant="light" @click="showTopUpModal = false">Cancel</BButton>
                <BButton variant="primary" @click="handleTopUp" :disabled="submitting">
                    <span v-if="submitting">
                        <span class="spinner-border spinner-border-sm me-1"></span>
                        Processing...
                    </span>
                    <span v-else>Continue to Payment</span>
                </BButton>
            </template>
        </BModal>
    </MainLayout>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { Icon } from '@iconify/vue'
import PageBreadcrumb from '@/components/PageBreadcrumb.vue'
import { usePageMeta } from '@/composables/usePageMeta'
import MainLayout from '@/layouts/MainLayout.vue'
import UICard from '@/components/UICard.vue'
import { billingService } from '@/services/billing.service'
import dayjs from 'dayjs'
import Swal from 'sweetalert2'

usePageMeta('Billing')

const reserveBalance = ref({
    reserve_balance_cents: 0,
    reserve_balance_dollars: '0.00'
})

const billingProfile = ref<any>(null)
const ledger = ref<any[]>([])
const loadingProfile = ref(false)
const loadingLedger = ref(false)
const openingPortal = ref(false)
const submitting = ref(false)
const showTopUpModal = ref(false)

const currentPage = ref(1)
const pageSize = ref(20)
const totalItems = ref(0)
const totalPages = ref(0)

const topUpForm = reactive({
    amount: 50
})

const formatDateTime = (date: string) => {
    return dayjs(date).format('MMM D, YYYY h:mm A')
}

const getEntryTypeBadge = (type: string) => {
    switch (type) {
        case 'credit':
        case 'topup':
            return 'success'
        case 'debit':
        case 'usage':
            return 'danger'
        case 'adjustment':
            return 'warning'
        default:
            return 'secondary'
    }
}

const fetchReserveBalance = async () => {
    try {
        const data = await billingService.getReserveBalance()
        reserveBalance.value = data
    } catch (error) {
        console.error('Failed to fetch reserve balance:', error)
    }
}

const fetchBillingProfile = async () => {
    loadingProfile.value = true
    try {
        const data = await billingService.getBillingProfile()
        billingProfile.value = data
    } catch (error) {
        console.error('Failed to fetch billing profile:', error)
    } finally {
        loadingProfile.value = false
    }
}

const fetchLedger = async () => {
    loadingLedger.value = true
    try {
        const params = {
            page: currentPage.value,
            limit: pageSize.value
        }

        const data = await billingService.getReserveLedger(params)
        ledger.value = data.results || []
        totalItems.value = data.count || 0
        totalPages.value = Math.ceil(totalItems.value / pageSize.value)
    } catch (error) {
        console.error('Failed to fetch ledger:', error)
        Swal.fire({
            icon: 'error',
            title: 'Error',
            text: 'Failed to load transaction history'
        })
    } finally {
        loadingLedger.value = false
    }
}

const handleTopUp = async () => {
    if (topUpForm.amount < 10 || topUpForm.amount > 1000) {
        Swal.fire({
            icon: 'error',
            title: 'Invalid Amount',
            text: 'Amount must be between $10 and $1,000'
        })
        return
    }

    submitting.value = true
    try {
        const response = await billingService.createTopUpSession({
            amount_cents: topUpForm.amount * 100
        })

        if (response.checkout_url) {
            // Redirect to Stripe Checkout
            window.location.href = response.checkout_url
        }
    } catch (error) {
        console.error('Failed to create top-up session:', error)
        Swal.fire({
            icon: 'error',
            title: 'Error',
            text: 'Failed to initiate payment. Please try again.'
        })
    } finally {
        submitting.value = false
    }
}

const openCustomerPortal = async () => {
    openingPortal.value = true
    try {
        const response = await billingService.createPortalSession()
        if (response.portal_url) {
            window.location.href = response.portal_url
        }
    } catch (error) {
        console.error('Failed to open customer portal:', error)
        Swal.fire({
            icon: 'error',
            title: 'Error',
            text: 'Failed to open billing portal. Please try again.'
        })
    } finally {
        openingPortal.value = false
    }
}

const exportLedger = async () => {
    try {
        const data = await billingService.exportLedger()
        
        // Create download link
        const blob = new Blob([data], { type: 'text/csv' })
        const url = window.URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = url
        link.download = `ledger_export_${dayjs().format('YYYY-MM-DD')}.csv`
        link.click()
        window.URL.revokeObjectURL(url)
        
        Swal.fire({
            icon: 'success',
            title: 'Exported!',
            text: 'Transaction history exported as CSV',
            timer: 2000,
            showConfirmButton: false
        })
    } catch (error) {
        console.error('Failed to export ledger:', error)
        Swal.fire({
            icon: 'error',
            title: 'Error',
            text: 'Failed to export transaction history'
        })
    }
}

const resetTopUpForm = () => {
    topUpForm.amount = 50
}

onMounted(() => {
    fetchReserveBalance()
    fetchBillingProfile()
    fetchLedger()
})
</script>

<style scoped>
.table th {
    font-weight: 600;
    text-transform: uppercase;
    font-size: 0.75rem;
    letter-spacing: 0.5px;
    color: #6c757d;
}
</style>
