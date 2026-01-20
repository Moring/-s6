<template>
    <MainLayout>
        <BContainer fluid>
            <PageBreadcrumb title="Epics" :items="[{ text: 'Worklog', to: '/worklog' }, { text: 'Epics', active: true }]" />
            
            <!-- AI Assistant -->
            <BRow class="mb-3">
                <BCol cols="12">
                    <AIChatInput 
                        placeholder="Ask me about organizing your work into epics..."
                        context="epics"
                    />
                </BCol>
            </BRow>

            <!-- Quick Actions -->
            <BRow class="mb-3">
                <BCol cols="12">
                    <div class="d-flex gap-2 justify-content-between align-items-center">
                        <div class="d-flex gap-2">
                            <BButton variant="outline-primary" size="sm" @click="$router.push('/worklog')">
                                <Icon icon="tabler:arrow-left" class="me-1" />
                                Back to Worklog
                            </BButton>
                            <BButton variant="outline-primary" size="sm" @click="$router.push('/worklog/projects')">
                                <Icon icon="tabler:folder" class="me-1" />
                                Projects
                            </BButton>
                        </div>
                        <BButton variant="primary" @click="openAddModal">
                            <Icon icon="tabler:plus" class="me-1" />
                            Add Epic
                        </BButton>
                    </div>
                </BCol>
            </BRow>

            <!-- Filters -->
            <BRow class="mb-3">
                <BCol cols="12">
                    <UICard>
                        <BRow class="align-items-end">
                            <BCol md="4">
                                <BFormGroup label="Search" label-for="search">
                                    <BFormInput
                                        id="search"
                                        v-model="search"
                                        placeholder="Search epics..."
                                        @input="debouncedSearch"
                                    />
                                </BFormGroup>
                            </BCol>
                            <BCol md="3">
                                <BFormGroup label="Project" label-for="filter-project">
                                    <BFormSelect
                                        id="filter-project"
                                        v-model="filterProject"
                                        :options="projectOptions"
                                        @change="fetchEpics"
                                    />
                                </BFormGroup>
                            </BCol>
                            <BCol md="2">
                                <BFormGroup label="Status" label-for="filter-status">
                                    <BFormSelect
                                        id="filter-status"
                                        v-model="filterStatus"
                                        :options="statusOptions"
                                        @change="fetchEpics"
                                    />
                                </BFormGroup>
                            </BCol>
                            <BCol md="2">
                                <BButton variant="light" class="w-100" @click="resetFilters">
                                    <Icon icon="tabler:filter-off" />
                                    Reset
                                </BButton>
                            </BCol>
                        </BRow>
                    </UICard>
                </BCol>
            </BRow>

            <!-- Epics List -->
            <BRow>
                <BCol cols="12">
                    <UICard title="Epics">
                        <div v-if="loading" class="text-center py-5">
                            <div class="spinner-border text-primary" role="status">
                                <span class="visually-hidden">Loading...</span>
                            </div>
                        </div>

                        <div v-else-if="epics.length === 0" class="text-center py-5 text-muted">
                            <Icon icon="tabler:layers-off" :width="64" :height="64" class="mb-3" />
                            <h5>No epics found</h5>
                            <p>Create your first epic to organize your work</p>
                            <BButton variant="primary" @click="openAddModal">
                                Create First Epic
                            </BButton>
                        </div>

                        <div v-else>
                            <BTable 
                                :items="epics" 
                                :fields="tableFields"
                                responsive
                                hover
                                striped
                            >
                                <template #cell(name)="data">
                                    <div>
                                        <strong>{{ data.item.name }}</strong>
                                        <div v-if="data.item.description" class="text-muted small">
                                            {{ truncateText(data.item.description, 100) }}
                                        </div>
                                    </div>
                                </template>

                                <template #cell(project)="data">
                                    <BBadge variant="info">{{ data.item.project_name }}</BBadge>
                                </template>

                                <template #cell(is_active)="data">
                                    <BBadge :variant="data.item.is_active ? 'success' : 'secondary'">
                                        {{ data.item.is_active ? 'Active' : 'Inactive' }}
                                    </BBadge>
                                </template>

                                <template #cell(actions)="data">
                                    <div class="d-flex gap-1">
                                        <BButton 
                                            variant="link" 
                                            size="sm" 
                                            @click="editEpic(data.item)"
                                            title="Edit"
                                        >
                                            <Icon icon="tabler:edit" />
                                        </BButton>
                                        <BButton 
                                            variant="link" 
                                            size="sm" 
                                            class="text-danger" 
                                            @click="deleteEpic(data.item)"
                                            title="Delete"
                                        >
                                            <Icon icon="tabler:trash" />
                                        </BButton>
                                    </div>
                                </template>
                            </BTable>

                            <!-- Pagination -->
                            <div v-if="totalPages > 1" class="d-flex justify-content-between align-items-center mt-4">
                                <div class="text-muted">
                                    Showing {{ (currentPage - 1) * pageSize + 1 }} to {{ Math.min(currentPage * pageSize, totalItems) }} of {{ totalItems }} epics
                                </div>
                                <BPagination
                                    v-model="currentPage"
                                    :total-rows="totalItems"
                                    :per-page="pageSize"
                                    @update:model-value="fetchEpics"
                                />
                            </div>
                        </div>
                    </UICard>
                </BCol>
            </BRow>
        </BContainer>

        <!-- Add/Edit Modal -->
        <BModal 
            v-model="showModal" 
            :title="editMode ? 'Edit Epic' : 'Add Epic'"
            size="lg"
            @ok="saveEpic"
        >
            <BForm @submit.prevent="saveEpic">
                <BFormGroup label="Project" label-for="epic-project" :class="{ 'mb-3': true }">
                    <BFormSelect
                        id="epic-project"
                        v-model="formData.project"
                        :options="projectOptions"
                        required
                    />
                </BFormGroup>

                <BFormGroup label="Name" label-for="epic-name" class="mb-3">
                    <BFormInput
                        id="epic-name"
                        v-model="formData.name"
                        required
                        placeholder="Epic name"
                    />
                </BFormGroup>

                <BFormGroup label="Description" label-for="epic-description" class="mb-3">
                    <BFormTextarea
                        id="epic-description"
                        v-model="formData.description"
                        rows="3"
                        placeholder="Describe this epic..."
                    />
                </BFormGroup>

                <BFormGroup class="mb-0">
                    <BFormCheckbox v-model="formData.is_active">
                        Active
                    </BFormCheckbox>
                </BFormGroup>
            </BForm>

            <template #footer="{ ok, cancel }">
                <BButton variant="secondary" @click="cancel()">Cancel</BButton>
                <BButton variant="primary" @click="ok()" :disabled="submitting">
                    <span v-if="submitting">
                        <span class="spinner-border spinner-border-sm me-1"></span>
                        Saving...
                    </span>
                    <span v-else>Save</span>
                </BButton>
            </template>
        </BModal>
    </MainLayout>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { Icon } from '@iconify/vue'
import PageBreadcrumb from '@/components/PageBreadcrumb.vue'
import AIChatInput from '@/components/AIChatInput.vue'
import { usePageMeta } from '@/composables/usePageMeta'
import MainLayout from '@/layouts/MainLayout.vue'
import UICard from '@/components/UICard.vue'
import { worklogService, type Epic, type Project } from '@/services/worklog.service'
import Swal from 'sweetalert2'
import { debounce } from 'lodash-es'

usePageMeta('Epics')

const epics = ref<Epic[]>([])
const projects = ref<Project[]>([])
const loading = ref(false)
const submitting = ref(false)
const showModal = ref(false)
const editMode = ref(false)
const search = ref('')
const filterProject = ref<number | null>(null)
const filterStatus = ref<string>('all')
const currentPage = ref(1)
const pageSize = ref(20)
const totalItems = ref(0)
const totalPages = computed(() => Math.ceil(totalItems.value / pageSize.value))

const formData = reactive({
    id: null as number | null,
    project: null as number | null,
    name: '',
    description: '',
    is_active: true
})

const tableFields = [
    { key: 'name', label: 'Name', sortable: true },
    { key: 'project', label: 'Project', sortable: true },
    { key: 'is_active', label: 'Status', sortable: true },
    { key: 'created_at', label: 'Created', sortable: true, formatter: (value: string) => new Date(value).toLocaleDateString() },
    { key: 'actions', label: 'Actions', class: 'text-end' }
]

const projectOptions = computed(() => [
    { value: null, text: 'All Projects' },
    ...projects.value.map(p => ({ value: p.id, text: p.name }))
])

const statusOptions = [
    { value: 'all', text: 'All' },
    { value: 'true', text: 'Active' },
    { value: 'false', text: 'Inactive' }
]

async function fetchProjects() {
    try {
        const response = await worklogService.getProjects()
        projects.value = response.results || []
    } catch (error) {
        console.error('Failed to fetch projects:', error)
    }
}

async function fetchEpics() {
    loading.value = true
    try {
        const params: any = {
            page: currentPage.value,
            page_size: pageSize.value
        }
        
        if (search.value) {
            params.search = search.value
        }
        
        if (filterProject.value) {
            params.project = filterProject.value
        }
        
        if (filterStatus.value !== 'all') {
            params.is_active = filterStatus.value
        }

        const response = await worklogService.getEpics(params)
        epics.value = response.results || []
        totalItems.value = response.count || 0
    } catch (error) {
        console.error('Failed to fetch epics:', error)
        await Swal.fire('Error', 'Failed to load epics', 'error')
    } finally {
        loading.value = false
    }
}

const debouncedSearch = debounce(() => {
    currentPage.value = 1
    fetchEpics()
}, 300)

function resetFilters() {
    search.value = ''
    filterProject.value = null
    filterStatus.value = 'all'
    currentPage.value = 1
    fetchEpics()
}

function openAddModal() {
    editMode.value = false
    formData.id = null
    formData.project = null
    formData.name = ''
    formData.description = ''
    formData.is_active = true
    showModal.value = true
}

function editEpic(epic: Epic) {
    editMode.value = true
    formData.id = epic.id
    formData.project = epic.project
    formData.name = epic.name
    formData.description = epic.description || ''
    formData.is_active = epic.is_active
    showModal.value = true
}

async function saveEpic() {
    if (!formData.project || !formData.name) {
        await Swal.fire('Error', 'Please fill in all required fields', 'error')
        return
    }

    submitting.value = true
    try {
        const data = {
            project: formData.project,
            name: formData.name,
            description: formData.description,
            is_active: formData.is_active
        }

        if (editMode.value && formData.id) {
            await worklogService.updateEpic(formData.id, data)
            await Swal.fire('Success', 'Epic updated successfully', 'success')
        } else {
            await worklogService.createEpic(data)
            await Swal.fire('Success', 'Epic created successfully', 'success')
        }

        showModal.value = false
        await fetchEpics()
    } catch (error: any) {
        console.error('Failed to save epic:', error)
        await Swal.fire('Error', error.response?.data?.detail || 'Failed to save epic', 'error')
    } finally {
        submitting.value = false
    }
}

async function deleteEpic(epic: Epic) {
    const result = await Swal.fire({
        title: 'Delete Epic?',
        text: `Are you sure you want to delete "${epic.name}"? This action cannot be undone.`,
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#d33',
        cancelButtonColor: '#3085d6',
        confirmButtonText: 'Yes, delete it'
    })

    if (result.isConfirmed) {
        try {
            await worklogService.deleteEpic(epic.id)
            await Swal.fire('Deleted!', 'Epic has been deleted.', 'success')
            await fetchEpics()
        } catch (error: any) {
            console.error('Failed to delete epic:', error)
            await Swal.fire('Error', error.response?.data?.detail || 'Failed to delete epic', 'error')
        }
    }
}

function truncateText(text: string, maxLength: number): string {
    if (!text || text.length <= maxLength) return text
    return text.substring(0, maxLength) + '...'
}

onMounted(async () => {
    await fetchProjects()
    await fetchEpics()
})
</script>

<style scoped>
.table {
    margin-bottom: 0;
}
</style>
