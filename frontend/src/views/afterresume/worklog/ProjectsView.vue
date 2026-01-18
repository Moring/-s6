<template>
    <MainLayout>
        <BContainer fluid>
            <PageBreadcrumb title="Projects" />
            
            <BRow class="mb-3">
                <BCol cols="12">
                    <AIChatInput 
                        placeholder="Ask me anything about your projects..."
                        context="projects"
                    />
                </BCol>
            </BRow>

            <!-- Filters -->
            <BRow class="mb-3">
                <BCol cols="12">
                    <UICard>
                        <BRow class="align-items-end">
                            <BCol md="6">
                                <BFormGroup label="Filter by Client" label-for="filter-client">
                                    <BFormSelect
                                        id="filter-client"
                                        v-model="selectedClient"
                                        :options="clientOptions"
                                        @change="fetchProjects"
                                    />
                                </BFormGroup>
                            </BCol>
                            <BCol md="3">
                                <BFormGroup>
                                    <BFormCheckbox v-model="showInactive" @change="fetchProjects">
                                        Show Inactive
                                    </BFormCheckbox>
                                </BFormGroup>
                            </BCol>
                            <BCol md="3">
                                <BButton variant="primary" class="w-100" @click="showAddModal = true">
                                    <Icon icon="tabler:plus" class="me-1" />
                                    Add Project
                                </BButton>
                            </BCol>
                        </BRow>
                    </UICard>
                </BCol>
            </BRow>

            <BRow>
                <BCol cols="12">
                    <UICard title="Projects">
                        <div v-if="loading" class="text-center py-5">
                            <div class="spinner-border text-primary" role="status">
                                <span class="visually-hidden">Loading...</span>
                            </div>
                        </div>

                        <div v-else-if="filteredProjects.length === 0" class="text-center py-5 text-muted">
                            <Icon icon="tabler:folder-off" :width="64" :height="64" class="mb-3" />
                            <h5>No projects found</h5>
                            <p>Add your first project to start organizing your work</p>
                            <BButton variant="primary" @click="showAddModal = true">
                                Add First Project
                            </BButton>
                        </div>

                        <div v-else>
                            <BTable 
                                :items="filteredProjects" 
                                :fields="fields"
                                striped 
                                hover 
                                responsive
                            >
                                <template #cell(client_name)="data">
                                    <BBadge variant="primary">{{ data.value }}</BBadge>
                                </template>

                                <template #cell(role)="data">
                                    <small class="text-muted">{{ data.value || 'N/A' }}</small>
                                </template>

                                <template #cell(dates)="data">
                                    <small>
                                        {{ formatDate(data.item.started_on) }} - 
                                        {{ data.item.ended_on ? formatDate(data.item.ended_on) : 'Present' }}
                                    </small>
                                </template>

                                <template #cell(is_active)="data">
                                    <BBadge :variant="data.value ? 'success' : 'secondary'">
                                        {{ data.value ? 'Active' : 'Inactive' }}
                                    </BBadge>
                                </template>

                                <template #cell(actions)="data">
                                    <div class="d-flex gap-2">
                                        <BButton variant="link" size="sm" @click="editProject(data.item)">
                                            <Icon icon="tabler:edit" />
                                        </BButton>
                                        <BButton 
                                            variant="link" 
                                            size="sm" 
                                            class="text-danger" 
                                            @click="deleteProject(data.item)"
                                        >
                                            <Icon icon="tabler:trash" />
                                        </BButton>
                                    </div>
                                </template>
                            </BTable>
                        </div>
                    </UICard>
                </BCol>
            </BRow>
        </BContainer>

        <!-- Add/Edit Modal -->
        <BModal
            v-model="showAddModal"
            :title="editMode ? 'Edit Project' : 'Add Project'"
            size="lg"
            @hidden="resetForm"
        >
            <BForm @submit.prevent="handleSubmit">
                <BFormGroup label="Client" label-for="project-client" class="mb-3">
                    <BFormSelect
                        id="project-client"
                        v-model="form.client"
                        :options="clientOptions"
                        required
                    />
                </BFormGroup>

                <BFormGroup label="Project Name" label-for="project-name" class="mb-3">
                    <BFormInput
                        id="project-name"
                        v-model="form.name"
                        placeholder="Project name"
                        required
                    />
                </BFormGroup>

                <BFormGroup label="Description" label-for="project-description" class="mb-3">
                    <BFormTextarea
                        id="project-description"
                        v-model="form.description"
                        placeholder="Brief description..."
                        rows="3"
                    />
                </BFormGroup>

                <BFormGroup label="Your Role" label-for="project-role" class="mb-3">
                    <BFormInput
                        id="project-role"
                        v-model="form.role"
                        placeholder="e.g., Senior Developer, Team Lead, Consultant"
                    />
                </BFormGroup>

                <BRow>
                    <BCol md="6">
                        <BFormGroup label="Start Date" label-for="project-start" class="mb-3">
                            <BFormInput
                                id="project-start"
                                v-model="form.started_on"
                                type="date"
                            />
                        </BFormGroup>
                    </BCol>
                    <BCol md="6">
                        <BFormGroup label="End Date" label-for="project-end" class="mb-3">
                            <BFormInput
                                id="project-end"
                                v-model="form.ended_on"
                                type="date"
                            />
                        </BFormGroup>
                    </BCol>
                </BRow>

                <BFormGroup class="mb-3">
                    <BFormCheckbox v-model="form.is_active">
                        Active
                    </BFormCheckbox>
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
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { Icon } from '@iconify/vue'
import PageBreadcrumb from '@/components/PageBreadcrumb.vue'
import AIChatInput from '@/components/AIChatInput.vue'
import { usePageMeta } from '@/composables/usePageMeta'
import MainLayout from '@/layouts/MainLayout.vue'
import UICard from '@/components/UICard.vue'
import { worklogService, type Client, type Project } from '@/services/worklog.service'
import dayjs from 'dayjs'
import Swal from 'sweetalert2'

usePageMeta('Projects')

const route = useRoute()
const projects = ref<Project[]>([])
const clients = ref<Client[]>([])
const loading = ref(false)
const submitting = ref(false)
const showAddModal = ref(false)
const editMode = ref(false)
const currentEditId = ref<number | null>(null)
const selectedClient = ref<number | null>(null)
const showInactive = ref(false)

const form = reactive({
    client: null as number | null,
    name: '',
    description: '',
    role: '',
    started_on: '',
    ended_on: '',
    is_active: true
})

const fields = [
    { key: 'name', label: 'Project Name', sortable: true },
    { key: 'client_name', label: 'Client' },
    { key: 'role', label: 'Your Role' },
    { key: 'dates', label: 'Duration' },
    { key: 'is_active', label: 'Status' },
    { key: 'actions', label: 'Actions' }
]

const clientOptions = computed(() => {
    return [
        { value: null, text: 'All Clients' },
        ...clients.value.map(c => ({ value: c.id, text: c.name }))
    ]
})

const filteredProjects = computed(() => {
    let filtered = projects.value

    if (selectedClient.value) {
        filtered = filtered.filter(p => p.client === selectedClient.value)
    }

    if (!showInactive.value) {
        filtered = filtered.filter(p => p.is_active)
    }

    return filtered
})

const formatDate = (date: string | null | undefined) => {
    if (!date) return 'N/A'
    return dayjs(date).format('MMM YYYY')
}

const fetchClients = async () => {
    try {
        clients.value = await worklogService.listClients()
    } catch (error) {
        console.error('Failed to fetch clients:', error)
    }
}

const fetchProjects = async () => {
    loading.value = true
    try {
        projects.value = await worklogService.listProjects(selectedClient.value || undefined)
    } catch (error) {
        console.error('Failed to fetch projects:', error)
        Swal.fire({
            icon: 'error',
            title: 'Error',
            text: 'Failed to load projects'
        })
    } finally {
        loading.value = false
    }
}

const handleSubmit = async () => {
    submitting.value = true
    try {
        if (editMode.value && currentEditId.value) {
            await worklogService.updateProject(currentEditId.value, form)
        } else {
            await worklogService.createProject(form)
        }

        showAddModal.value = false
        resetForm()

        Swal.fire({
            icon: 'success',
            title: 'Success!',
            text: editMode.value ? 'Project updated successfully' : 'Project created successfully',
            timer: 2000,
            showConfirmButton: false
        })

        fetchProjects()
    } catch (error: any) {
        console.error('Failed to save project:', error)
        Swal.fire({
            icon: 'error',
            title: 'Error',
            text: error.message || 'Failed to save project'
        })
    } finally {
        submitting.value = false
    }
}

const editProject = (project: Project) => {
    editMode.value = true
    currentEditId.value = project.id
    form.client = project.client
    form.name = project.name
    form.description = project.description || ''
    form.role = project.role || ''
    form.started_on = project.started_on || ''
    form.ended_on = project.ended_on || ''
    form.is_active = project.is_active
    showAddModal.value = true
}

const deleteProject = async (project: Project) => {
    const result = await Swal.fire({
        title: 'Are you sure?',
        text: 'This will permanently delete this project',
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#d33',
        cancelButtonColor: '#3085d6',
        confirmButtonText: 'Yes, delete it!'
    })

    if (result.isConfirmed) {
        try {
            await worklogService.deleteProject(project.id)
            Swal.fire({
                icon: 'success',
                title: 'Deleted!',
                text: 'Project has been deleted',
                timer: 2000,
                showConfirmButton: false
            })
            fetchProjects()
        } catch (error) {
            console.error('Failed to delete project:', error)
            Swal.fire({
                icon: 'error',
                title: 'Error',
                text: 'Failed to delete project'
            })
        }
    }
}

const resetForm = () => {
    editMode.value = false
    currentEditId.value = null
    form.client = null
    form.name = ''
    form.description = ''
    form.role = ''
    form.started_on = ''
    form.ended_on = ''
    form.is_active = true
}

onMounted(async () => {
    await fetchClients()
    
    // Check if client filter is in query params
    if (route.query.client) {
        selectedClient.value = parseInt(route.query.client as string)
    }
    
    await fetchProjects()
})
</script>
