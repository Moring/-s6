<template>
    <MainLayout>
        <BContainer fluid>
            <PageBreadcrumb title="Admin Dashboard" />

            <!-- System Controls -->
            <BRow class="mb-3">
                <BCol cols="12">
                    <UICard title="System Controls">
                        <div v-if="loadingControls" class="text-center py-3">
                            <div class="spinner-border text-primary" role="status">
                                <span class="visually-hidden">Loading...</span>
                            </div>
                        </div>
                        <div v-else>
                            <BRow>
                                <BCol md="6" class="mb-3">
                                    <h6 class="mb-3">Incident Switches</h6>
                                    <div class="d-flex justify-content-between align-items-center mb-2">
                                        <span>Maintenance Mode</span>
                                        <BBadge :variant="systemControls.maintenance_mode ? 'danger' : 'success'">
                                            {{ systemControls.maintenance_mode ? 'ON' : 'OFF' }}
                                        </BBadge>
                                    </div>
                                    <div class="d-flex justify-content-between align-items-center">
                                        <span>Disable Sharing</span>
                                        <BBadge :variant="systemControls.disable_sharing ? 'warning' : 'success'">
                                            {{ systemControls.disable_sharing ? 'DISABLED' : 'ENABLED' }}
                                        </BBadge>
                                    </div>
                                </BCol>
                                <BCol md="6" class="mb-3">
                                    <h6 class="mb-3">Feature Flags</h6>
                                    <div v-for="(value, key) in systemControls.feature_flags" :key="key" 
                                         class="d-flex justify-content-between align-items-center mb-2">
                                        <span class="text-capitalize">{{ key.replace(/_/g, ' ') }}</span>
                                        <BBadge :variant="value ? 'success' : 'secondary'">
                                            {{ value ? 'ON' : 'OFF' }}
                                        </BBadge>
                                    </div>
                                </BCol>
                            </BRow>
                        </div>
                    </UICard>
                </BCol>
            </BRow>

            <!-- Stats Cards -->
            <BRow class="mb-3">
                <BCol md="3" class="mb-3">
                    <UICard>
                        <div class="text-center">
                            <Icon icon="tabler:users" :width="40" :height="40" class="text-primary mb-2" />
                            <h3 class="mb-1">{{ stats.total_users }}</h3>
                            <small class="text-muted">Total Users</small>
                        </div>
                    </UICard>
                </BCol>
                <BCol md="3" class="mb-3">
                    <UICard>
                        <div class="text-center">
                            <Icon icon="tabler:key" :width="40" :height="40" class="text-success mb-2" />
                            <h3 class="mb-1">{{ stats.active_passkeys }}</h3>
                            <small class="text-muted">Active Passkeys</small>
                        </div>
                    </UICard>
                </BCol>
                <BCol md="3" class="mb-3">
                    <UICard>
                        <div class="text-center">
                            <Icon icon="tabler:alert-triangle" :width="40" :height="40" class="text-danger mb-2" />
                            <h3 class="mb-1">{{ stats.failed_jobs }}</h3>
                            <small class="text-muted">Failed Jobs</small>
                        </div>
                    </UICard>
                </BCol>
                <BCol md="3" class="mb-3">
                    <UICard>
                        <div class="text-center">
                            <Icon icon="tabler:clock" :width="40" :height="40" class="text-info mb-2" />
                            <h3 class="mb-1">{{ stats.audit_events }}</h3>
                            <small class="text-muted">Recent Events</small>
                        </div>
                    </UICard>
                </BCol>
            </BRow>

            <!-- Tabs for Different Admin Sections -->
            <BRow>
                <BCol cols="12">
                    <UICard>
                        <BTabs content-class="mt-3">
                            <!-- Users Tab -->
                            <BTab title="Users" active>
                                <div class="mb-3">
                                    <BInputGroup>
                                        <BFormInput v-model="userSearch" placeholder="Search users..." />
                                        <BButton @click="fetchUsers" variant="primary">Search</BButton>
                                    </BInputGroup>
                                </div>
                                <div v-if="loadingUsers" class="text-center py-5">
                                    <div class="spinner-border text-primary" role="status">
                                        <span class="visually-hidden">Loading...</span>
                                    </div>
                                </div>
                                <div v-else-if="users.length === 0" class="text-center py-5 text-muted">
                                    <p>No users found</p>
                                </div>
                                <div v-else class="table-responsive">
                                    <table class="table table-hover">
                                        <thead>
                                            <tr>
                                                <th>ID</th>
                                                <th>Username</th>
                                                <th>Email</th>
                                                <th>Tenant</th>
                                                <th>Status</th>
                                                <th>Staff</th>
                                                <th>Actions</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            <tr v-for="user in users" :key="user.id">
                                                <td>{{ user.id }}</td>
                                                <td>{{ user.username }}</td>
                                                <td>{{ user.email }}</td>
                                                <td>{{ user.tenant_id || 'N/A' }}</td>
                                                <td>
                                                    <BBadge :variant="user.is_active ? 'success' : 'secondary'">
                                                        {{ user.is_active ? 'Active' : 'Inactive' }}
                                                    </BBadge>
                                                </td>
                                                <td>
                                                    <BBadge :variant="user.is_staff ? 'primary' : 'light'">
                                                        {{ user.is_staff ? 'Yes' : 'No' }}
                                                    </BBadge>
                                                </td>
                                                <td>
                                                    <BButton size="sm" variant="outline-primary" @click="viewUser(user)">
                                                        View
                                                    </BButton>
                                                </td>
                                            </tr>
                                        </tbody>
                                    </table>
                                </div>
                            </BTab>

                            <!-- Passkeys Tab -->
                            <BTab title="Invite Passkeys">
                                <div class="mb-3">
                                    <BButton @click="showCreatePasskey = true" variant="primary">
                                        <Icon icon="tabler:plus" class="me-1" />
                                        Create Passkey
                                    </BButton>
                                </div>
                                <div v-if="loadingPasskeys" class="text-center py-5">
                                    <div class="spinner-border text-primary" role="status">
                                        <span class="visually-hidden">Loading...</span>
                                    </div>
                                </div>
                                <div v-else-if="passkeys.length === 0" class="text-center py-5 text-muted">
                                    <p>No passkeys found</p>
                                </div>
                                <div v-else class="table-responsive">
                                    <table class="table table-hover">
                                        <thead>
                                            <tr>
                                                <th>ID</th>
                                                <th>Key</th>
                                                <th>Expires At</th>
                                                <th>Uses</th>
                                                <th>Status</th>
                                                <th>Tenant Scope</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            <tr v-for="passkey in passkeys" :key="passkey.id">
                                                <td>{{ passkey.id }}</td>
                                                <td><code>{{ passkey.key }}</code></td>
                                                <td>{{ formatDate(passkey.expires_at) }}</td>
                                                <td>{{ passkey.uses_count }} / {{ passkey.max_uses }}</td>
                                                <td>
                                                    <BBadge :variant="passkey.is_active ? 'success' : 'secondary'">
                                                        {{ passkey.is_active ? 'Active' : 'Used/Expired' }}
                                                    </BBadge>
                                                </td>
                                                <td>{{ passkey.tenant_scope || 'Any' }}</td>
                                            </tr>
                                        </tbody>
                                    </table>
                                </div>
                            </BTab>

                            <!-- Failed Jobs Tab -->
                            <BTab title="Failed Jobs">
                                <div v-if="loadingFailedJobs" class="text-center py-5">
                                    <div class="spinner-border text-primary" role="status">
                                        <span class="visually-hidden">Loading...</span>
                                    </div>
                                </div>
                                <div v-else-if="failedJobs.length === 0" class="text-center py-5 text-muted">
                                    <Icon icon="tabler:check-circle" :width="48" :height="48" class="mb-3 text-success" />
                                    <p>No failed jobs</p>
                                </div>
                                <div v-else class="table-responsive">
                                    <table class="table table-hover">
                                        <thead>
                                            <tr>
                                                <th>ID</th>
                                                <th>Status</th>
                                                <th>Error</th>
                                                <th>Created</th>
                                                <th>Actions</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            <tr v-for="job in failedJobs" :key="job.id">
                                                <td><code>{{ job.id }}</code></td>
                                                <td>
                                                    <BBadge variant="danger">{{ job.status }}</BBadge>
                                                </td>
                                                <td class="text-truncate" style="max-width: 300px;">
                                                    {{ job.error }}
                                                </td>
                                                <td>{{ formatDate(job.created_at) }}</td>
                                                <td>
                                                    <BButton size="sm" variant="outline-primary" @click="retryJob(job.id)">
                                                        Retry
                                                    </BButton>
                                                </td>
                                            </tr>
                                        </tbody>
                                    </table>
                                </div>
                            </BTab>

                            <!-- Audit Log Tab -->
                            <BTab title="Audit Log">
                                <div v-if="loadingAuditEvents" class="text-center py-5">
                                    <div class="spinner-border text-primary" role="status">
                                        <span class="visually-hidden">Loading...</span>
                                    </div>
                                </div>
                                <div v-else-if="auditEvents.length === 0" class="text-center py-5 text-muted">
                                    <p>No audit events found</p>
                                </div>
                                <div v-else class="table-responsive">
                                    <table class="table table-hover table-sm">
                                        <thead>
                                            <tr>
                                                <th>ID</th>
                                                <th>Event Type</th>
                                                <th>User</th>
                                                <th>Timestamp</th>
                                                <th>Metadata</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            <tr v-for="event in auditEvents" :key="event.id">
                                                <td>{{ event.id }}</td>
                                                <td><BBadge variant="info">{{ event.event_type }}</BBadge></td>
                                                <td>{{ event.user_id || 'System' }}</td>
                                                <td>{{ formatDate(event.timestamp) }}</td>
                                                <td class="text-truncate" style="max-width: 200px;">
                                                    {{ event.metadata ? JSON.stringify(event.metadata).substring(0, 50) : '-' }}
                                                </td>
                                            </tr>
                                        </tbody>
                                    </table>
                                </div>
                            </BTab>
                        </BTabs>
                    </UICard>
                </BCol>
            </BRow>

            <!-- Create Passkey Modal -->
            <BModal v-model="showCreatePasskey" title="Create Invite Passkey" @ok="createPasskey">
                <BFormGroup label="Expiration Date" label-for="expires-at">
                    <BFormInput id="expires-at" v-model="newPasskey.expires_at" type="datetime-local" required />
                </BFormGroup>
                <BFormGroup label="Max Uses" label-for="max-uses">
                    <BFormInput id="max-uses" v-model.number="newPasskey.max_uses" type="number" :min="1" />
                </BFormGroup>
                <BFormGroup label="Tenant Scope (Optional)" label-for="tenant-scope">
                    <BFormInput id="tenant-scope" v-model.number="newPasskey.tenant_scope" type="number" />
                </BFormGroup>
                <BFormGroup label="Notes (Optional)" label-for="notes">
                    <BFormTextarea id="notes" v-model="newPasskey.notes" rows="3" />
                </BFormGroup>
            </BModal>
        </BContainer>
    </MainLayout>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Icon } from '@iconify/vue'
import PageBreadcrumb from '@/components/PageBreadcrumb.vue'
import { usePageMeta } from '@/composables/usePageMeta'
import MainLayout from '@/layouts/MainLayout.vue'
import UICard from '@/components/UICard.vue'
import { adminService } from '@/services/admin.service'
import type { AdminUser, AdminPasskey, AuditEvent, FailedJob, SystemControls } from '@/services/admin.service'
import dayjs from 'dayjs'

usePageMeta('Admin Dashboard')

const systemControls = ref<SystemControls>({
    maintenance_mode: false,
    disable_sharing: false,
    feature_flags: {
        sharing: true,
        exports: true,
        ai_workflows: true,
        email_notifications: false,
        stripe: false
    },
    rate_limiting_enabled: true,
    service_health: {}
})

const stats = ref({
    total_users: 0,
    active_passkeys: 0,
    failed_jobs: 0,
    audit_events: 0
})

const users = ref<AdminUser[]>([])
const passkeys = ref<AdminPasskey[]>([])
const failedJobs = ref<FailedJob[]>([])
const auditEvents = ref<AuditEvent[]>([])

const loadingControls = ref(true)
const loadingUsers = ref(true)
const loadingPasskeys = ref(true)
const loadingFailedJobs = ref(true)
const loadingAuditEvents = ref(true)

const userSearch = ref('')
const showCreatePasskey = ref(false)
const newPasskey = ref({
    expires_at: '',
    max_uses: 1,
    tenant_scope: undefined as number | undefined,
    notes: ''
})

const formatDate = (date: string) => {
    return dayjs(date).format('MMM D, YYYY HH:mm')
}

const fetchSystemControls = async () => {
    loadingControls.value = true
    try {
        const data = await adminService.getSystemControls()
        systemControls.value = data
    } catch (error) {
        console.error('Failed to fetch system controls:', error)
    } finally {
        loadingControls.value = false
    }
}

const fetchUsers = async () => {
    loadingUsers.value = true
    try {
        const data = await adminService.listUsers({ search: userSearch.value || undefined })
        users.value = data.results || []
        stats.value.total_users = users.value.length
    } catch (error) {
        console.error('Failed to fetch users:', error)
    } finally {
        loadingUsers.value = false
    }
}

const fetchPasskeys = async () => {
    loadingPasskeys.value = true
    try {
        const data = await adminService.listPasskeys()
        passkeys.value = data.results || []
        stats.value.active_passkeys = passkeys.value.filter(p => p.is_active).length
    } catch (error) {
        console.error('Failed to fetch passkeys:', error)
    } finally {
        loadingPasskeys.value = false
    }
}

const fetchFailedJobs = async () => {
    loadingFailedJobs.value = true
    try {
        const data = await adminService.listFailedJobs(50)
        failedJobs.value = data.results || []
        stats.value.failed_jobs = failedJobs.value.length
    } catch (error) {
        console.error('Failed to fetch failed jobs:', error)
    } finally {
        loadingFailedJobs.value = false
    }
}

const fetchAuditEvents = async () => {
    loadingAuditEvents.value = true
    try {
        const data = await adminService.listAuditEvents({ limit: 100 })
        auditEvents.value = data.results || []
        stats.value.audit_events = auditEvents.value.length
    } catch (error) {
        console.error('Failed to fetch audit events:', error)
    } finally {
        loadingAuditEvents.value = false
    }
}

const createPasskey = async () => {
    try {
        await adminService.createPasskey(newPasskey.value)
        showCreatePasskey.value = false
        newPasskey.value = {
            expires_at: '',
            max_uses: 1,
            tenant_scope: undefined,
            notes: ''
        }
        await fetchPasskeys()
    } catch (error) {
        console.error('Failed to create passkey:', error)
        alert('Failed to create passkey')
    }
}

const retryJob = async (jobId: string) => {
    try {
        await adminService.retryFailedJob(jobId)
        await fetchFailedJobs()
    } catch (error) {
        console.error('Failed to retry job:', error)
        alert('Failed to retry job')
    }
}

const viewUser = (user: AdminUser) => {
    alert(`User details for ${user.username} (TODO: implement detail view)`)
}

onMounted(() => {
    fetchSystemControls()
    fetchUsers()
    fetchPasskeys()
    fetchFailedJobs()
    fetchAuditEvents()
})
</script>

<style scoped>
.text-truncate {
    max-width: 300px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
</style>
