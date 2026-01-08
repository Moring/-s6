<template>
    <MainLayout>
        <BContainer fluid>
            <PageBreadcrumb title="Reports" />

            <!-- Generate Report Section -->
            <BRow class="mb-3">
                <BCol cols="12">
                    <UICard title="Generate New Report">
                        <BForm @submit.prevent="handleGenerateReport">
                            <BRow>
                                <BCol md="3">
                                    <BFormGroup label="Report Type" label-for="report-type">
                                        <BFormSelect
                                            id="report-type"
                                            v-model="generateForm.kind"
                                            :options="reportTypes"
                                            required
                                        />
                                    </BFormGroup>
                                </BCol>
                                <BCol md="3">
                                    <BFormGroup label="Start Date" label-for="start-date">
                                        <BFormInput
                                            id="start-date"
                                            v-model="generateForm.startDate"
                                            type="date"
                                            required
                                        />
                                    </BFormGroup>
                                </BCol>
                                <BCol md="3">
                                    <BFormGroup label="End Date" label-for="end-date">
                                        <BFormInput
                                            id="end-date"
                                            v-model="generateForm.endDate"
                                            type="date"
                                            required
                                        />
                                    </BFormGroup>
                                </BCol>
                                <BCol md="3" class="d-flex align-items-end">
                                    <BFormGroup class="w-100">
                                        <BButton type="submit" variant="primary" class="w-100" :disabled="generating">
                                            <span v-if="generating">
                                                <span class="spinner-border spinner-border-sm me-1"></span>
                                                Generating...
                                            </span>
                                            <span v-else>
                                                <Icon icon="tabler:report" class="me-1" />
                                                Generate Report
                                            </span>
                                        </BButton>
                                    </BFormGroup>
                                </BCol>
                            </BRow>
                        </BForm>
                    </UICard>
                </BCol>
            </BRow>

            <!-- Filters -->
            <BRow class="mb-3">
                <BCol cols="12">
                    <UICard>
                        <BRow class="align-items-end">
                            <BCol md="4">
                                <BFormGroup label="Filter by Type" label-for="filter-type">
                                    <BFormSelect
                                        id="filter-type"
                                        v-model="filters.kind"
                                        :options="filterTypes"
                                        @change="fetchReports"
                                    />
                                </BFormGroup>
                            </BCol>
                            <BCol md="3">
                                <BFormGroup label="Start Date" label-for="filter-start">
                                    <BFormInput
                                        id="filter-start"
                                        v-model="filters.startDate"
                                        type="date"
                                        @change="fetchReports"
                                    />
                                </BFormGroup>
                            </BCol>
                            <BCol md="3">
                                <BFormGroup label="End Date" label-for="filter-end">
                                    <BFormInput
                                        id="filter-end"
                                        v-model="filters.endDate"
                                        type="date"
                                        @change="fetchReports"
                                    />
                                </BFormGroup>
                            </BCol>
                            <BCol md="2">
                                <BButton variant="light" class="w-100" @click="resetFilters">
                                    <Icon icon="tabler:filter-off" class="me-1" />
                                    Reset
                                </BButton>
                            </BCol>
                        </BRow>
                    </UICard>
                </BCol>
            </BRow>

            <!-- Reports List -->
            <BRow>
                <BCol cols="12">
                    <UICard title="Generated Reports">
                        <div v-if="loading" class="text-center py-5">
                            <div class="spinner-border text-primary" role="status">
                                <span class="visually-hidden">Loading...</span>
                            </div>
                        </div>

                        <div v-else-if="reports.length === 0" class="text-center py-5 text-muted">
                            <Icon icon="tabler:report-off" :width="64" :height="64" class="mb-3" />
                            <h5>No reports generated yet</h5>
                            <p>Generate your first report using the form above</p>
                        </div>

                        <div v-else>
                            <div v-for="report in reports" :key="report.id" class="report-item border-bottom py-3">
                                <div class="d-flex justify-content-between align-items-start mb-2">
                                    <div class="flex-grow-1">
                                        <div class="d-flex align-items-center gap-2 mb-2">
                                            <h6 class="mb-0">{{ getReportTypeLabel(report.kind) }}</h6>
                                            <BBadge :variant="getReportBadge(report.kind)">
                                                {{ report.kind }}
                                            </BBadge>
                                        </div>
                                        <small class="text-muted d-block">
                                            Created: {{ formatDateTime(report.created_at) }}
                                        </small>
                                        <small v-if="report.updated_at !== report.created_at" class="text-muted d-block">
                                            Updated: {{ formatDateTime(report.updated_at) }}
                                        </small>
                                    </div>
                                    <div class="d-flex gap-2">
                                        <BButton variant="outline-primary" size="sm" @click="viewReport(report)">
                                            <Icon icon="tabler:eye" class="me-1" />
                                            View
                                        </BButton>
                                        <BButton variant="outline-secondary" size="sm" @click="downloadReport(report)">
                                            <Icon icon="tabler:download" class="me-1" />
                                            Download
                                        </BButton>
                                        <BButton variant="outline-danger" size="sm" @click="deleteReport(report)">
                                            <Icon icon="tabler:trash" />
                                        </BButton>
                                    </div>
                                </div>
                            </div>

                            <!-- Pagination -->
                            <div v-if="totalPages > 1" class="d-flex justify-content-between align-items-center mt-4">
                                <div class="text-muted">
                                    Showing {{ (currentPage - 1) * pageSize + 1 }} to {{ Math.min(currentPage * pageSize, totalItems) }} of {{ totalItems }} reports
                                </div>
                                <BPagination
                                    v-model="currentPage"
                                    :total-rows="totalItems"
                                    :per-page="pageSize"
                                    @update:model-value="fetchReports"
                                />
                            </div>
                        </div>
                    </UICard>
                </BCol>
            </BRow>
        </BContainer>

        <!-- View Report Modal -->
        <BModal
            v-model="showViewModal"
            :title="selectedReport ? getReportTypeLabel(selectedReport.kind) : 'Report'"
            size="xl"
            scrollable
        >
            <div v-if="selectedReport">
                <div class="mb-3">
                    <small class="text-muted">Generated: {{ formatDateTime(selectedReport.created_at) }}</small>
                </div>
                
                <!-- Rendered HTML Content -->
                <div v-if="selectedReport.rendered_html" class="report-content" v-html="selectedReport.rendered_html"></div>
                
                <!-- Fallback to text -->
                <div v-else-if="selectedReport.rendered_text" class="report-content">
                    <pre class="p-3 bg-light rounded">{{ selectedReport.rendered_text }}</pre>
                </div>
                
                <!-- Raw content if nothing else -->
                <div v-else-if="selectedReport.content" class="report-content">
                    <pre class="p-3 bg-light rounded">{{ JSON.stringify(selectedReport.content, null, 2) }}</pre>
                </div>
            </div>

            <template #footer>
                <BButton variant="secondary" @click="downloadReport(selectedReport)">
                    <Icon icon="tabler:download" class="me-1" />
                    Download
                </BButton>
                <BButton variant="light" @click="showViewModal = false">Close</BButton>
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
import { reportService } from '@/services/report.service'
import dayjs from 'dayjs'
import Swal from 'sweetalert2'

usePageMeta('Reports')

const reports = ref<any[]>([])
const selectedReport = ref<any>(null)
const loading = ref(false)
const generating = ref(false)
const showViewModal = ref(false)

const currentPage = ref(1)
const pageSize = ref(10)
const totalItems = ref(0)
const totalPages = ref(0)

const reportTypes = [
    { value: 'resume', text: 'Resume' },
    { value: 'status', text: 'Status Report' },
    { value: 'standup', text: 'Standup' },
    { value: 'summary', text: 'Summary' }
]

const filterTypes = [
    { value: 'all', text: 'All Types' },
    ...reportTypes
]

const generateForm = reactive({
    kind: 'summary',
    startDate: dayjs().subtract(7, 'days').format('YYYY-MM-DD'),
    endDate: dayjs().format('YYYY-MM-DD')
})

const filters = reactive({
    kind: 'all',
    startDate: '',
    endDate: ''
})

const formatDateTime = (date: string) => {
    return dayjs(date).format('MMM D, YYYY h:mm A')
}

const getReportTypeLabel = (kind: string) => {
    const type = reportTypes.find(t => t.value === kind)
    return type ? type.text : kind
}

const getReportBadge = (kind: string) => {
    switch (kind) {
        case 'resume':
            return 'primary'
        case 'status':
            return 'info'
        case 'standup':
            return 'warning'
        case 'summary':
            return 'success'
        default:
            return 'secondary'
    }
}

const resetFilters = () => {
    filters.kind = 'all'
    filters.startDate = ''
    filters.endDate = ''
    fetchReports()
}

const fetchReports = async () => {
    loading.value = true
    try {
        const params: any = {
            page: currentPage.value,
            limit: pageSize.value
        }

        if (filters.kind !== 'all') params.kind = filters.kind
        if (filters.startDate) params.start_date = filters.startDate
        if (filters.endDate) params.end_date = filters.endDate

        const data = await reportService.listReports(params)
        reports.value = data.results || []
        totalItems.value = data.count || 0
        totalPages.value = Math.ceil(totalItems.value / pageSize.value)
    } catch (error) {
        console.error('Failed to fetch reports:', error)
        Swal.fire({
            icon: 'error',
            title: 'Error',
            text: 'Failed to load reports'
        })
    } finally {
        loading.value = false
    }
}

const handleGenerateReport = async () => {
    generating.value = true
    try {
        const payload = {
            kind: generateForm.kind,
            start_date: generateForm.startDate,
            end_date: generateForm.endDate
        }

        await reportService.generateReport(payload)

        Swal.fire({
            icon: 'success',
            title: 'Report Queued!',
            text: 'Your report is being generated. This may take a few moments.',
            timer: 3000
        })

        // Refresh after a delay
        setTimeout(() => {
            fetchReports()
        }, 5000)
    } catch (error) {
        console.error('Failed to generate report:', error)
        Swal.fire({
            icon: 'error',
            title: 'Error',
            text: 'Failed to generate report'
        })
    } finally {
        generating.value = false
    }
}

const viewReport = (report: any) => {
    selectedReport.value = report
    showViewModal.value = true
}

const downloadReport = (report: any) => {
    if (!report) return
    
    const content = report.rendered_html || report.rendered_text || JSON.stringify(report.content, null, 2)
    const blob = new Blob([content], { type: 'text/html' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `report_${report.kind}_${dayjs(report.created_at).format('YYYY-MM-DD')}.html`
    link.click()
    window.URL.revokeObjectURL(url)
}

const deleteReport = async (report: any) => {
    const result = await Swal.fire({
        title: 'Are you sure?',
        text: 'This will permanently delete this report',
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#d33',
        cancelButtonColor: '#3085d6',
        confirmButtonText: 'Yes, delete it!'
    })

    if (result.isConfirmed) {
        try {
            await reportService.deleteReport(report.id)
            Swal.fire({
                icon: 'success',
                title: 'Deleted!',
                text: 'Report has been deleted',
                timer: 2000,
                showConfirmButton: false
            })
            fetchReports()
        } catch (error) {
            console.error('Failed to delete report:', error)
            Swal.fire({
                icon: 'error',
                title: 'Error',
                text: 'Failed to delete report'
            })
        }
    }
}

onMounted(() => {
    fetchReports()
})
</script>

<style scoped>
.report-item {
    transition: background-color 0.2s;
}

.report-item:hover {
    background-color: rgba(0, 0, 0, 0.02);
}

.report-item:last-child {
    border-bottom: none !important;
}

.report-content {
    max-height: 600px;
    overflow-y: auto;
}

.report-content pre {
    white-space: pre-wrap;
    word-wrap: break-word;
}
</style>
