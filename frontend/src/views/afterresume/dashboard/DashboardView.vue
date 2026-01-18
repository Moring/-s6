<template>
  <MainLayout>
    <BContainer fluid>
      <PageBreadcrumb title="Dashboard" :items="breadcrumbItems" />

      <!-- Welcome Section -->
      <BRow class="mb-4">
        <BCol cols="12">
          <BCard class="border-0 shadow-sm">
            <BCardBody>
              <h4 class="mb-1">Welcome back, {{ user?.username }}!</h4>
              <p class="text-muted mb-0">Here's what's happening with your career documentation</p>
            </BCardBody>
          </BCard>
        </BCol>
      </BRow>

      <!-- Stats Row -->
      <BRow class="mb-4">
        <BCol xl="3" md="6">
          <BCard class="border-0 shadow-sm">
            <BCardBody>
              <div class="d-flex align-items-center">
                <div class="flex-shrink-0">
                  <div class="avatar-sm rounded-circle bg-primary bg-opacity-10 text-primary fs-4 d-flex align-items-center justify-content-center">
                    <i class="ri-file-list-3-line"></i>
                  </div>
                </div>
                <div class="flex-grow-1 ms-3">
                  <p class="text-muted mb-1">Work Entries</p>
                  <h4 class="mb-0">{{ stats.worklog_count || 0 }}</h4>
                </div>
              </div>
            </BCardBody>
          </BCard>
        </BCol>

        <BCol xl="3" md="6">
          <BCard class="border-0 shadow-sm">
            <BCardBody>
              <div class="d-flex align-items-center">
                <div class="flex-shrink-0">
                  <div class="avatar-sm rounded-circle bg-success bg-opacity-10 text-success fs-4 d-flex align-items-center justify-content-center">
                    <i class="ri-star-line"></i>
                  </div>
                </div>
                <div class="flex-grow-1 ms-3">
                  <p class="text-muted mb-1">Skills Tracked</p>
                  <h4 class="mb-0">{{ stats.skills_count || 0 }}</h4>
                </div>
              </div>
            </BCardBody>
          </BCard>
        </BCol>

        <BCol xl="3" md="6">
          <BCard class="border-0 shadow-sm">
            <BCardBody>
              <div class="d-flex align-items-center">
                <div class="flex-shrink-0">
                  <div class="avatar-sm rounded-circle bg-info bg-opacity-10 text-info fs-4 d-flex align-items-center justify-content-center">
                    <i class="ri-file-text-line"></i>
                  </div>
                </div>
                <div class="flex-grow-1 ms-3">
                  <p class="text-muted mb-1">Reports Generated</p>
                  <h4 class="mb-0">{{ stats.reports_count || 0 }}</h4>
                </div>
              </div>
            </BCardBody>
          </BCard>
        </BCol>

        <BCol xl="3" md="6">
          <BCard class="border-0 shadow-sm">
            <BCardBody>
              <div class="d-flex align-items-center">
                <div class="flex-shrink-0">
                  <div class="avatar-sm rounded-circle bg-warning bg-opacity-10 text-warning fs-4 d-flex align-items-center justify-content-center">
                    <i class="ri-wallet-line"></i>
                  </div>
                </div>
                <div class="flex-grow-1 ms-3">
                  <p class="text-muted mb-1">Reserve Balance</p>
                  <h4 class="mb-0">${{ reserveBalance }}</h4>
                </div>
              </div>
            </BCardBody>
          </BCard>
        </BCol>
      </BRow>

      <!-- Quick Actions -->
      <BRow class="mb-4">
        <BCol cols="12">
          <BCard class="border-0 shadow-sm">
            <BCardBody>
              <h5 class="card-title mb-3">Quick Actions</h5>
              <BRow class="g-3">
                <BCol md="3" sm="6">
                  <BButton
                    variant="outline-primary"
                    class="w-100 d-flex flex-column align-items-center py-3"
                    @click="navigateTo('/worklog')"
                  >
                    <i class="ri-add-circle-line fs-3 mb-2"></i>
                    <span>Add Work Entry</span>
                  </BButton>
                </BCol>
                <BCol md="3" sm="6">
                  <BButton
                    variant="outline-success"
                    class="w-100 d-flex flex-column align-items-center py-3"
                    @click="navigateTo('/skills')"
                  >
                    <i class="ri-lightbulb-line fs-3 mb-2"></i>
                    <span>View Skills</span>
                  </BButton>
                </BCol>
                <BCol md="3" sm="6">
                  <BButton
                    variant="outline-info"
                    class="w-100 d-flex flex-column align-items-center py-3"
                    @click="navigateTo('/reports')"
                  >
                    <i class="ri-file-chart-line fs-3 mb-2"></i>
                    <span>Generate Report</span>
                  </BButton>
                </BCol>
                <BCol md="3" sm="6">
                  <BButton
                    variant="outline-warning"
                    class="w-100 d-flex flex-column align-items-center py-3"
                    @click="navigateTo('/billing')"
                  >
                    <i class="ri-bank-card-line fs-3 mb-2"></i>
                    <span>Manage Billing</span>
                  </BButton>
                </BCol>
              </BRow>
            </BCardBody>
          </BCard>
        </BCol>
      </BRow>

      <!-- Recent Activity -->
      <BRow>
        <BCol lg="8">
          <BCard class="border-0 shadow-sm">
            <BCardBody>
              <h5 class="card-title mb-3">Recent Work Entries</h5>
              
              <div v-if="loadingEntries" class="text-center py-4">
                <div class="spinner-border text-primary" role="status">
                  <span class="visually-hidden">Loading...</span>
                </div>
              </div>

              <div v-else-if="!recentEntries.length" class="text-center py-4">
                <p class="text-muted">No work entries yet. Start documenting your work!</p>
              </div>

              <div v-else class="list-group list-group-flush">
                <div
                  v-for="entry in recentEntries"
                  :key="entry.id"
                  class="list-group-item px-0"
                >
                  <div class="d-flex align-items-start">
                    <div class="flex-grow-1">
                      <h6 class="mb-1">{{ formatDate(entry.occurred_on) }}</h6>
                      <p class="mb-1 text-truncate">{{ entry.content }}</p>
                      <small class="text-muted">{{ formatTimeAgo(entry.created_at || '') }}</small>
                    </div>
                    <BButton
                      size="sm"
                      variant="link"
                      @click="navigateTo(`/worklog/${entry.id}`)"
                    >
                      View
                    </BButton>
                  </div>
                </div>
              </div>

              <div class="text-center mt-3">
                <BButton variant="link" @click="navigateTo('/worklog')">
                  View all entries <i class="ri-arrow-right-line"></i>
                </BButton>
              </div>
            </BCardBody>
          </BCard>
        </BCol>

        <BCol lg="4">
          <BCard class="border-0 shadow-sm mb-3">
            <BCardBody>
              <h5 class="card-title mb-3">System Status</h5>
              
              <div v-if="loadingStatus" class="text-center py-4">
                <div class="spinner-border text-primary spinner-border-sm" role="status">
                  <span class="visually-hidden">Loading...</span>
                </div>
              </div>

              <div v-else>
                <div class="d-flex justify-content-between align-items-center mb-2">
                  <span class="text-muted">Jobs Running</span>
                  <BBadge variant="primary" pill>{{ statusBar.jobs_running || 0 }}</BBadge>
                </div>
                <div class="d-flex justify-content-between align-items-center mb-2">
                  <span class="text-muted">Tokens Used</span>
                  <span class="fw-semibold">{{ formatNumber(statusBar.tokens_in + statusBar.tokens_out) }}</span>
                </div>
                <div class="d-flex justify-content-between align-items-center">
                  <span class="text-muted">Last Updated</span>
                  <small class="text-muted">{{ formatTimeAgo(statusBar.updated_at) }}</small>
                </div>
              </div>
            </BCardBody>
          </BCard>

          <BCard class="border-0 shadow-sm">
            <BCardBody>
              <h5 class="card-title mb-3">Getting Started</h5>
              <ul class="list-unstyled">
                <li class="mb-2">
                  <i class="ri-check-line text-success me-2"></i>
                  <span>Add your first work entry</span>
                </li>
                <li class="mb-2">
                  <i class="ri-check-line text-success me-2"></i>
                  <span>Upload supporting documents</span>
                </li>
                <li class="mb-2">
                  <i class="ri-check-line text-success me-2"></i>
                  <span>Let AI extract your skills</span>
                </li>
                <li class="mb-2">
                  <i class="ri-check-line text-success me-2"></i>
                  <span>Generate your first report</span>
                </li>
              </ul>
            </BCardBody>
          </BCard>
        </BCol>
      </BRow>
    </BContainer>
  </MainLayout>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import MainLayout from '@/layouts/main.vue'
import PageBreadcrumb from '@/components/PageBreadcrumb.vue'
import { useAuthStore } from '@/stores/auth'
import { usePageMeta } from '@/composables/usePageMeta'
import worklogService, { type WorkLog } from '@/services/worklog.service'
import skillService from '@/services/skill.service'
import reportService from '@/services/report.service'
import billingService from '@/services/billing.service'
import systemService, { type StatusBarData } from '@/services/system.service'

usePageMeta('Dashboard')

const router = useRouter()
const authStore = useAuthStore()

const user = computed(() => authStore.user)

const breadcrumbItems = [
  { text: 'AfterResume', href: '/' },
  { text: 'Dashboard', active: true }
]

// State
const stats = ref({
  worklog_count: 0,
  skills_count: 0,
  reports_count: 0
})

const statusBar = ref<StatusBarData>({
  reserve_balance_cents: 0,
  reserve_balance_dollars: 0,
  tokens_in: 0,
  tokens_out: 0,
  jobs_running: 0,
  updated_at: new Date().toISOString()
})

const reserveBalance = computed(() => {
  return (statusBar.value.reserve_balance_cents / 100).toFixed(2)
})

const recentEntries = ref<WorkLog[]>([])
const loadingEntries = ref(false)
const loadingStatus = ref(false)

// Methods
const navigateTo = (path: string) => {
  router.push(path)
}

const loadStats = async () => {
  try {
    // Load worklog count
    const worklogResponse = await worklogService.list({ page: 1 })
    stats.value.worklog_count = worklogResponse.count

    // Load skills count
    const skillsResponse = await skillService.list({ page: 1 })
    stats.value.skills_count = skillsResponse.count

    // Load reports count
    const reportsResponse = await reportService.list({ page: 1 })
    stats.value.reports_count = reportsResponse.count
  } catch (error) {
    console.error('Failed to load stats:', error)
  }
}

const loadRecentEntries = async () => {
  loadingEntries.value = true
  try {
    const response = await worklogService.list({ page: 1 })
    recentEntries.value = response.results.slice(0, 5)
  } catch (error) {
    console.error('Failed to load recent entries:', error)
  } finally {
    loadingEntries.value = false
  }
}

const loadStatusBar = async () => {
  loadingStatus.value = true
  try {
    statusBar.value = await systemService.getStatusBar()
  } catch (error) {
    console.error('Failed to load status bar:', error)
  } finally {
    loadingStatus.value = false
  }
}

const formatDate = (dateStr: string) => {
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric'
  })
}

const formatTimeAgo = (dateStr: string) => {
  const date = new Date(dateStr)
  const now = new Date()
  const seconds = Math.floor((now.getTime() - date.getTime()) / 1000)

  if (seconds < 60) return 'just now'
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  if (days < 7) return `${days}d ago`
  return formatDate(dateStr)
}

const formatNumber = (num: number) => {
  if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M'
  if (num >= 1000) return (num / 1000).toFixed(1) + 'K'
  return num.toString()
}

// Lifecycle
onMounted(() => {
  loadStats()
  loadRecentEntries()
  loadStatusBar()
})
</script>

<style scoped>
.avatar-sm {
  width: 48px;
  height: 48px;
}

.list-group-item {
  border-left: 0;
  border-right: 0;
}

.list-group-item:first-child {
  border-top: 0;
}

.list-group-item:last-child {
  border-bottom: 0;
}
</style>
