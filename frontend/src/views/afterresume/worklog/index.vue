<template>
    <MainLayout>
        <BContainer fluid>
            <PageBreadcrumb title="Worklog" />
            
            <!-- Quick Add Section -->
            <BRow class="mb-3">
                <BCol cols="12">
                    <UICard title="Quick Add Entry">
                        <BForm @submit.prevent="handleQuickAdd">
                            <BRow>
                                <BCol md="3">
                                    <BFormGroup label="Date" label-for="quick-date">
                                        <BFormInput
                                            id="quick-date"
                                            v-model="quickAdd.date"
                                            type="date"
                                            required
                                        />
                                    </BFormGroup>
                                </BCol>
                                <BCol md="7">
                                    <BFormGroup label="What did you work on?" label-for="quick-content">
                                        <BFormTextarea
                                            id="quick-content"
                                            v-model="quickAdd.content"
                                            placeholder="Describe your work..."
                                            rows="3"
                                            required
                                        />
                                    </BFormGroup>
                                </BCol>
                                <BCol md="2" class="d-flex align-items-end">
                                    <BFormGroup class="w-100">
                                        <BButton type="submit" variant="primary" class="w-100" :disabled="submitting">
                                            <span v-if="submitting">
                                                <span class="spinner-border spinner-border-sm me-1"></span>
                                                Saving...
                                            </span>
                                            <span v-else>Add Entry</span>
                                        </BButton>
                                    </BFormGroup>
                                </BCol>
                            </BRow>
                        </BForm>
                    </UICard>
                </BCol>
            </BRow>

            <!-- Filters and Search -->
            <BRow class="mb-3">
                <BCol cols="12">
                    <UICard>
                        <BRow class="align-items-end">
                            <BCol md="4">
                                <BFormGroup label="Search" label-for="search">
                                    <BFormInput
                                        id="search"
                                        v-model="filters.search"
                                        placeholder="Search entries..."
                                        @input="debouncedSearch"
                                    />
                                </BFormGroup>
                            </BCol>
                            <BCol md="3">
                                <BFormGroup label="Start Date" label-for="start-date">
                                    <BFormInput
                                        id="start-date"
                                        v-model="filters.startDate"
                                        type="date"
                                        @change="fetchWorklogs"
                                    />
                                </BFormGroup>
                            </BCol>
                            <BCol md="3">
                                <BFormGroup label="End Date" label-for="end-date">
                                    <BFormInput
                                        id="end-date"
                                        v-model="filters.endDate"
                                        type="date"
                                        @change="fetchWorklogs"
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

            <!-- Worklog Entries List -->
            <BRow>
                <BCol cols="12">
                    <UICard title="Work Entries">
                        <template #actions>
                            <BButton variant="primary" size="sm" @click="showAddModal = true">
                                <Icon icon="tabler:plus" class="me-1" />
                                Add Detailed Entry
                            </BButton>
                        </template>

                        <div v-if="loading" class="text-center py-5">
                            <div class="spinner-border text-primary" role="status">
                                <span class="visually-hidden">Loading...</span>
                            </div>
                        </div>

                        <div v-else-if="worklogs.length === 0" class="text-center py-5 text-muted">
                            <Icon icon="tabler:notebook-off" :width="64" :height="64" class="mb-3" />
                            <h5>No worklog entries found</h5>
                            <p>Start tracking your work by adding your first entry</p>
                            <BButton variant="primary" @click="showAddModal = true">
                                Create First Entry
                            </BButton>
                        </div>

                        <div v-else>
                            <div v-for="entry in worklogs" :key="entry.id" class="worklog-entry border-bottom py-3">
                                <div class="d-flex justify-content-between align-items-start mb-2">
                                    <div>
                                        <h6 class="mb-1">
                                            <Icon icon="tabler:calendar" class="me-1" />
                                            {{ formatDate(entry.date) }}
                                        </h6>
                                        <small class="text-muted">
                                            Created: {{ formatDateTime(entry.created_at) }}
                                            <span v-if="entry.updated_at !== entry.created_at">
                                                | Updated: {{ formatDateTime(entry.updated_at) }}
                                            </span>
                                        </small>
                                    </div>
                                    <div class="d-flex gap-2">
                                        <BBadge variant="light">{{ entry.source }}</BBadge>
                                        <BButton variant="link" size="sm" @click="editEntry(entry)">
                                            <Icon icon="tabler:edit" />
                                        </BButton>
                                        <BButton variant="link" size="sm" class="text-danger" @click="deleteEntry(entry)">
                                            <Icon icon="tabler:trash" />
                                        </BButton>
                                    </div>
                                </div>
                                <div class="content mb-2">
                                    <p class="mb-0">{{ entry.content }}</p>
                                </div>
                                <div v-if="entry.attachments && entry.attachments.length > 0" class="attachments">
                                    <small class="text-muted d-block mb-1">Attachments:</small>
                                    <div class="d-flex flex-wrap gap-2">
                                        <BBadge v-for="att in entry.attachments" :key="att.id" variant="info">
                                            <Icon icon="tabler:paperclip" class="me-1" />
                                            {{ att.filename }}
                                        </BBadge>
                                    </div>
                                </div>
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
                                    @update:model-value="fetchWorklogs"
                                />
                            </div>
                        </div>
                    </UICard>
                </BCol>
            </BRow>
        </BContainer>

        <!-- Add/Edit Modal -->
        <BModal
            v-model="showAddModal"
            :title="editMode ? 'Edit Entry' : 'Add Detailed Entry'"
            size="lg"
            @hidden="resetForm"
        >
            <BForm @submit.prevent="handleSubmit">
                <BFormGroup label="Date" label-for="entry-date" class="mb-3">
                    <BFormInput
                        id="entry-date"
                        v-model="form.date"
                        type="date"
                        required
                    />
                </BFormGroup>

                <BFormGroup label="Content" label-for="entry-content" class="mb-3">
                    <BFormTextarea
                        id="entry-content"
                        v-model="form.content"
                        placeholder="Describe your work in detail..."
                        rows="6"
                        required
                    />
                </BFormGroup>

                <BFormGroup label="Source" label-for="entry-source" class="mb-3">
                    <BFormInput
                        id="entry-source"
                        v-model="form.source"
                        placeholder="e.g., manual, standup, etc."
                    />
                </BFormGroup>

                <BFormGroup label="Metadata (JSON)" label-for="entry-metadata" class="mb-3">
                    <BFormTextarea
                        id="entry-metadata"
                        v-model="form.metadataStr"
                        placeholder='{"key": "value"}'
                        rows="3"
                    />
                    <small class="text-muted">Optional: Add structured metadata as JSON</small>
                </BFormGroup>
            </BForm>

            <template #footer>
                <BButton variant="light" @click="showAddModal = false">Cancel</BButton>
                <BButton variant="primary" @click="handleSubmit" :disabled="submitting">
                    <span v-if="submitting">
                        <span class="spinner-border spinner-border-sm me-1"></span>
                        Saving...
                    </span>
                    <span v-else>{{ editMode ? 'Update' : 'Save' }}</span>
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
import { worklogService } from '@/services/worklog.service'
import dayjs from 'dayjs'
import Swal from 'sweetalert2'

usePageMeta('Worklog')

const worklogs = ref<any[]>([])
const loading = ref(false)
const submitting = ref(false)
const showAddModal = ref(false)
const editMode = ref(false)
const currentEditId = ref<number | null>(null)

const currentPage = ref(1)
const pageSize = ref(10)
const totalItems = ref(0)
const totalPages = ref(0)

const quickAdd = reactive({
    date: dayjs().format('YYYY-MM-DD'),
    content: ''
})

const form = reactive({
    date: dayjs().format('YYYY-MM-DD'),
    content: '',
    source: 'manual',
    metadataStr: '{}'
})

const filters = reactive({
    search: '',
    startDate: '',
    endDate: ''
})

let searchTimeout: any = null

const debouncedSearch = () => {
    clearTimeout(searchTimeout)
    searchTimeout = setTimeout(() => {
        fetchWorklogs()
    }, 500)
}

const formatDate = (date: string) => {
    return dayjs(date).format('MMMM D, YYYY')
}

const formatDateTime = (date: string) => {
    return dayjs(date).format('MMM D, YYYY h:mm A')
}

const resetFilters = () => {
    filters.search = ''
    filters.startDate = ''
    filters.endDate = ''
    fetchWorklogs()
}

const fetchWorklogs = async () => {
    loading.value = true
    try {
        const params: any = {
            page: currentPage.value,
            limit: pageSize.value
        }

        if (filters.search) params.search = filters.search
        if (filters.startDate) params.start_date = filters.startDate
        if (filters.endDate) params.end_date = filters.endDate

        const data = await worklogService.listWorklogs(params)
        worklogs.value = data.results || []
        totalItems.value = data.count || 0
        totalPages.value = Math.ceil(totalItems.value / pageSize.value)
    } catch (error) {
        console.error('Failed to fetch worklogs:', error)
        Swal.fire({
            icon: 'error',
            title: 'Error',
            text: 'Failed to load worklog entries'
        })
    } finally {
        loading.value = false
    }
}

const handleQuickAdd = async () => {
    submitting.value = true
    try {
        await worklogService.createWorklog({
            date: quickAdd.date,
            content: quickAdd.content,
            source: 'quick_add',
            metadata: {}
        })

        quickAdd.content = ''
        quickAdd.date = dayjs().format('YYYY-MM-DD')

        Swal.fire({
            icon: 'success',
            title: 'Success!',
            text: 'Entry added successfully',
            timer: 2000,
            showConfirmButton: false
        })

        fetchWorklogs()
    } catch (error) {
        console.error('Failed to create worklog:', error)
        Swal.fire({
            icon: 'error',
            title: 'Error',
            text: 'Failed to add entry'
        })
    } finally {
        submitting.value = false
    }
}

const handleSubmit = async () => {
    submitting.value = true
    try {
        let metadata = {}
        if (form.metadataStr) {
            try {
                metadata = JSON.parse(form.metadataStr)
            } catch {
                throw new Error('Invalid JSON in metadata field')
            }
        }

        const payload = {
            date: form.date,
            content: form.content,
            source: form.source || 'manual',
            metadata
        }

        if (editMode.value && currentEditId.value) {
            await worklogService.updateWorklog(currentEditId.value, payload)
        } else {
            await worklogService.createWorklog(payload)
        }

        showAddModal.value = false
        resetForm()

        Swal.fire({
            icon: 'success',
            title: 'Success!',
            text: editMode.value ? 'Entry updated successfully' : 'Entry created successfully',
            timer: 2000,
            showConfirmButton: false
        })

        fetchWorklogs()
    } catch (error: any) {
        console.error('Failed to save worklog:', error)
        Swal.fire({
            icon: 'error',
            title: 'Error',
            text: error.message || 'Failed to save entry'
        })
    } finally {
        submitting.value = false
    }
}

const editEntry = (entry: any) => {
    editMode.value = true
    currentEditId.value = entry.id
    form.date = entry.date
    form.content = entry.content
    form.source = entry.source || 'manual'
    form.metadataStr = JSON.stringify(entry.metadata || {}, null, 2)
    showAddModal.value = true
}

const deleteEntry = async (entry: any) => {
    const result = await Swal.fire({
        title: 'Are you sure?',
        text: 'This will permanently delete this worklog entry',
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#d33',
        cancelButtonColor: '#3085d6',
        confirmButtonText: 'Yes, delete it!'
    })

    if (result.isConfirmed) {
        try {
            await worklogService.deleteWorklog(entry.id)
            Swal.fire({
                icon: 'success',
                title: 'Deleted!',
                text: 'Entry has been deleted',
                timer: 2000,
                showConfirmButton: false
            })
            fetchWorklogs()
        } catch (error) {
            console.error('Failed to delete worklog:', error)
            Swal.fire({
                icon: 'error',
                title: 'Error',
                text: 'Failed to delete entry'
            })
        }
    }
}

const resetForm = () => {
    editMode.value = false
    currentEditId.value = null
    form.date = dayjs().format('YYYY-MM-DD')
    form.content = ''
    form.source = 'manual'
    form.metadataStr = '{}'
}

onMounted(() => {
    fetchWorklogs()
})
</script>

<style scoped>
.worklog-entry {
    transition: background-color 0.2s;
}

.worklog-entry:hover {
    background-color: rgba(0, 0, 0, 0.02);
}

.worklog-entry:last-child {
    border-bottom: none !important;
}

.content {
    white-space: pre-wrap;
}
</style>
