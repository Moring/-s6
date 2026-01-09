<template>
    <MainLayout>
        <BContainer fluid>
            <PageBreadcrumb title="Dashboard" />
            
            <!-- Status Bar - Reserve Balance & Tokens -->
            <BRow class="mb-3">
                <BCol cols="12">
                    <UICard>
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <h6 class="mb-1">Reserve Balance</h6>
                                <h3 class="mb-0">${{ statusBar.reserve_balance_dollars }}</h3>
                                <small class="text-muted">{{ statusBar.reserve_balance_cents }} cents</small>
                            </div>
                            <div class="text-end">
                                <h6 class="mb-1">Token Usage</h6>
                                <div class="d-flex gap-3">
                                    <div>
                                        <small class="text-muted d-block">In</small>
                                        <strong>{{ statusBar.tokens_in }}</strong>
                                    </div>
                                    <div>
                                        <small class="text-muted d-block">Out</small>
                                        <strong>{{ statusBar.tokens_out }}</strong>
                                    </div>
                                </div>
                            </div>
                            <div class="text-end">
                                <h6 class="mb-1">Jobs Running</h6>
                                <h3 class="mb-0">{{ statusBar.jobs_running }}</h3>
                            </div>
                            <div class="text-end">
                                <small class="text-muted">Last updated</small>
                                <div>{{ formatDate(statusBar.updated_at) }}</div>
                            </div>
                        </div>
                    </UICard>
                </BCol>
            </BRow>

            <!-- Quick Action Cards -->
            <BRow class="mb-3">
                <BCol md="6" lg="3" class="mb-3">
                    <UICard>
                        <div class="text-center p-3">
                            <Icon icon="tabler:notebook" class="text-primary" :width="48" :height="48" />
                            <h5 class="mt-3 mb-2">Worklog</h5>
                            <p class="text-muted mb-3">Track your daily work entries</p>
                            <BButton variant="primary" size="sm" @click="navigateTo('/worklog')">
                                Go to Worklog
                            </BButton>
                        </div>
                    </UICard>
                </BCol>
                
                <BCol md="6" lg="3" class="mb-3">
                    <UICard>
                        <div class="text-center p-3">
                            <Icon icon="tabler:upload" class="text-success" :width="48" :height="48" />
                            <h5 class="mt-3 mb-2">Upload</h5>
                            <p class="text-muted mb-3">Upload documents and files</p>
                            <BButton variant="success" size="sm" @click="navigateTo('/artifacts')">
                                Upload Files
                            </BButton>
                        </div>
                    </UICard>
                </BCol>
                
                <BCol md="6" lg="3" class="mb-3">
                    <UICard>
                        <div class="text-center p-3">
                            <Icon icon="tabler:report" class="text-info" :width="48" :height="48" />
                            <h5 class="mt-3 mb-2">Reports</h5>
                            <p class="text-muted mb-3">Generate and view reports</p>
                            <BButton variant="info" size="sm" @click="navigateTo('/reports')">
                                View Reports
                            </BButton>
                        </div>
                    </UICard>
                </BCol>
                
                <BCol md="6" lg="3" class="mb-3">
                    <UICard>
                        <div class="text-center p-3">
                            <Icon icon="tabler:credit-card" class="text-warning" :width="48" :height="48" />
                            <h5 class="mt-3 mb-2">Billing</h5>
                            <p class="text-muted mb-3">Manage your billing</p>
                            <BButton variant="warning" size="sm" @click="navigateTo('/billing')">
                                Manage Billing
                            </BButton>
                        </div>
                    </UICard>
                </BCol>
            </BRow>

            <!-- Recent Activity & Stats -->
            <BRow>
                <BCol lg="8" class="mb-3">
                    <UICard title="Recent Worklog Entries">
                        <div v-if="loading" class="text-center py-5">
                            <div class="spinner-border text-primary" role="status">
                                <span class="visually-hidden">Loading...</span>
                            </div>
                        </div>
                        <div v-else-if="recentWorklogs.length === 0" class="text-center py-5 text-muted">
                            <Icon icon="tabler:notebook-off" :width="48" :height="48" class="mb-3" />
                            <p>No worklog entries yet. Create your first entry!</p>
                            <BButton variant="primary" size="sm" @click="navigateTo('/worklog')">
                                Add Worklog Entry
                            </BButton>
                        </div>
                        <div v-else>
                            <div v-for="entry in recentWorklogs" :key="entry.id" class="border-bottom py-3">
                                <div class="d-flex justify-content-between align-items-start">
                                    <div>
                                        <h6 class="mb-1">{{ formatDate(entry.date) }}</h6>
                                        <p class="mb-0 text-muted small">{{ truncateText(entry.content, 100) }}</p>
                                    </div>
                                    <BBadge variant="light">{{ entry.source }}</BBadge>
                                </div>
                            </div>
                            <div class="text-center mt-3">
                                <BButton variant="link" @click="navigateTo('/worklog')">
                                    View All Entries
                                </BButton>
                            </div>
                        </div>
                    </UICard>
                </BCol>
                
                <BCol lg="4" class="mb-3">
                    <UICard title="Skills Overview">
                        <div v-if="loadingSkills" class="text-center py-5">
                            <div class="spinner-border text-primary" role="status">
                                <span class="visually-hidden">Loading...</span>
                            </div>
                        </div>
                        <div v-else-if="skills.length === 0" class="text-center py-5 text-muted">
                            <Icon icon="tabler:certificate-off" :width="48" :height="48" class="mb-3" />
                            <p>No skills extracted yet</p>
                        </div>
                        <div v-else>
                            <div v-for="skill in skills.slice(0, 5)" :key="skill.id" class="mb-2">
                                <div class="d-flex justify-content-between align-items-center">
                                    <span>{{ skill.name }}</span>
                                    <BBadge :variant="getConfidenceBadge(skill.confidence)">
                                        {{ (skill.confidence * 100).toFixed(0) }}%
                                    </BBadge>
                                </div>
                            </div>
                            <div class="text-center mt-3">
                                <BButton variant="link" @click="navigateTo('/skills')">
                                    View All Skills
                                </BButton>
                            </div>
                        </div>
                    </UICard>
                    
                    <UICard title="Gamification" class="mt-3">
                        <div v-if="loadingGamification" class="text-center py-3">
                            <div class="spinner-border text-primary spinner-border-sm" role="status">
                                <span class="visually-hidden">Loading...</span>
                            </div>
                        </div>
                        <div v-else>
                            <div class="text-center mb-3">
                                <Icon icon="tabler:award" :width="48" :height="48" class="text-warning" />
                                <h4 class="mt-2 mb-0">{{ gamification.total_xp || 0 }} XP</h4>
                                <small class="text-muted">Total Experience</small>
                            </div>
                            <div class="mb-2">
                                <div class="d-flex justify-content-between mb-1">
                                    <small>Level {{ gamification.level || 1 }}</small>
                                    <small>{{ gamification.xp_to_next_level || 0 }} XP to next level</small>
                                </div>
                                <BProgress :value="gamification.level_progress || 0" :max="100" variant="warning" />
                            </div>
                            <hr />
                            <div>
                                <h6 class="mb-2">Recent Badges</h6>
                                <div v-if="gamification.badges && gamification.badges.length > 0" class="d-flex flex-wrap gap-2">
                                    <BBadge v-for="badge in gamification.badges.slice(0, 3)" :key="badge" variant="success">
                                        {{ badge }}
                                    </BBadge>
                                </div>
                                <p v-else class="text-muted small mb-0">No badges earned yet</p>
                            </div>
                        </div>
                    </UICard>
                </BCol>
            </BRow>
        </BContainer>
    </MainLayout>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Icon } from '@iconify/vue'
import PageBreadcrumb from '@/components/PageBreadcrumb.vue'
import { usePageMeta } from '@/composables/usePageMeta'
import MainLayout from '@/layouts/MainLayout.vue'
import UICard from '@/components/UICard.vue'
import { worklogService } from '@/services/worklog.service'
import { skillService } from '@/services/skill.service'
import { systemService } from '@/services/system.service'
import dayjs from 'dayjs'

usePageMeta('Dashboard')

const router = useRouter()

const statusBar = ref({
    reserve_balance_cents: 0,
    reserve_balance_dollars: '0.00',
    tokens_in: 0,
    tokens_out: 0,
    jobs_running: 0,
    updated_at: new Date().toISOString()
})

const recentWorklogs = ref<any[]>([])
const skills = ref<any[]>([])
const gamification = ref<any>({})
const loading = ref(true)
const loadingSkills = ref(true)
const loadingGamification = ref(true)

const navigateTo = (path: string) => {
    router.push(`/afterresume${path}`)
}

const formatDate = (date: string) => {
    return dayjs(date).format('MMM D, YYYY')
}

const truncateText = (text: string, maxLength: number) => {
    if (text.length <= maxLength) return text
    return text.substring(0, maxLength) + '...'
}

const getConfidenceBadge = (confidence: number) => {
    if (confidence >= 0.8) return 'success'
    if (confidence >= 0.6) return 'info'
    if (confidence >= 0.4) return 'warning'
    return 'light'
}

const fetchStatusBar = async () => {
    try {
        const data = await systemService.getStatusBar()
        statusBar.value = data
    } catch (error) {
        console.error('Failed to fetch status bar:', error)
    }
}

const fetchRecentWorklogs = async () => {
    loading.value = true
    try {
        const data = await worklogService.listWorklogs({ limit: 5 })
        recentWorklogs.value = data.results || []
    } catch (error) {
        console.error('Failed to fetch worklogs:', error)
    } finally {
        loading.value = false
    }
}

const fetchSkills = async () => {
    loadingSkills.value = true
    try {
        const data = await skillService.listSkills({ limit: 5 })
        skills.value = data.results || []
    } catch (error) {
        console.error('Failed to fetch skills:', error)
    } finally {
        loadingSkills.value = false
    }
}

const fetchGamification = async () => {
    loadingGamification.value = true
    try {
        const data = await systemService.getGamificationSummary()
        gamification.value = data
    } catch (error) {
        console.error('Failed to fetch gamification:', error)
    } finally {
        loadingGamification.value = false
    }
}

onMounted(() => {
    fetchStatusBar()
    fetchRecentWorklogs()
    fetchSkills()
    fetchGamification()
    
    // Auto-refresh status bar every 30 seconds
    setInterval(fetchStatusBar, 30000)
})
</script>

<style scoped>
.border-bottom:last-child {
    border-bottom: none !important;
}
</style>
