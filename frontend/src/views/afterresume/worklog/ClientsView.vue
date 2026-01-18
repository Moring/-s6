<template>
    <MainLayout>
        <BContainer fluid>
            <PageBreadcrumb title="Clients & Employers" />
            
            <BRow class="mb-3">
                <BCol cols="12">
                    <AIChatInput 
                        placeholder="Ask me anything about your clients and employers..."
                        context="clients"
                    />
                </BCol>
            </BRow>

            <BRow>
                <BCol cols="12">
                    <UICard title="Clients & Employers">
                        <template #actions>
                            <BButton variant="primary" size="sm" @click="showAddModal = true">
                                <Icon icon="tabler:plus" class="me-1" />
                                Add Client
                            </BButton>
                        </template>

                        <div v-if="loading" class="text-center py-5">
                            <div class="spinner-border text-primary" role="status">
                                <span class="visually-hidden">Loading...</span>
                            </div>
                        </div>

                        <div v-else-if="clients.length === 0" class="text-center py-5 text-muted">
                            <Icon icon="tabler:building-off" :width="64" :height="64" class="mb-3" />
                            <h5>No clients found</h5>
                            <p>Add your first client or employer to start organizing your work</p>
                            <BButton variant="primary" @click="showAddModal = true">
                                Add First Client
                            </BButton>
                        </div>

                        <div v-else>
                            <BTable 
                                :items="clients" 
                                :fields="fields"
                                striped 
                                hover 
                                responsive
                            >
                                <template #cell(is_active)="data">
                                    <BBadge :variant="data.value ? 'success' : 'secondary'">
                                        {{ data.value ? 'Active' : 'Inactive' }}
                                    </BBadge>
                                </template>

                                <template #cell(projects_count)="data">
                                    <BBadge variant="info">{{ data.value || 0 }} projects</BBadge>
                                </template>

                                <template #cell(actions)="data">
                                    <div class="d-flex gap-2">
                                        <BButton 
                                            variant="link" 
                                            size="sm" 
                                            @click="viewProjects(data.item)"
                                            title="View Projects"
                                        >
                                            <Icon icon="tabler:folder" />
                                        </BButton>
                                        <BButton variant="link" size="sm" @click="editClient(data.item)">
                                            <Icon icon="tabler:edit" />
                                        </BButton>
                                        <BButton 
                                            variant="link" 
                                            size="sm" 
                                            class="text-danger" 
                                            @click="deleteClient(data.item)"
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
            :title="editMode ? 'Edit Client' : 'Add Client'"
            size="lg"
            @hidden="resetForm"
        >
            <BForm @submit.prevent="handleSubmit">
                <BFormGroup label="Name" label-for="client-name" class="mb-3">
                    <BFormInput
                        id="client-name"
                        v-model="form.name"
                        placeholder="Client or Employer name"
                        required
                    />
                </BFormGroup>

                <BFormGroup label="Description" label-for="client-description" class="mb-3">
                    <BFormTextarea
                        id="client-description"
                        v-model="form.description"
                        placeholder="Brief description..."
                        rows="3"
                    />
                </BFormGroup>

                <BFormGroup label="Website" label-for="client-website" class="mb-3">
                    <BFormInput
                        id="client-website"
                        v-model="form.website"
                        type="url"
                        placeholder="https://example.com"
                    />
                </BFormGroup>

                <BFormGroup label="Notes" label-for="client-notes" class="mb-3">
                    <BFormTextarea
                        id="client-notes"
                        v-model="form.notes"
                        placeholder="Internal notes..."
                        rows="3"
                    />
                </BFormGroup>

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
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Icon } from '@iconify/vue'
import PageBreadcrumb from '@/components/PageBreadcrumb.vue'
import AIChatInput from '@/components/AIChatInput.vue'
import { usePageMeta } from '@/composables/usePageMeta'
import MainLayout from '@/layouts/MainLayout.vue'
import UICard from '@/components/UICard.vue'
import { worklogService, type Client } from '@/services/worklog.service'
import Swal from 'sweetalert2'

usePageMeta('Clients & Employers')

const router = useRouter()
const clients = ref<Client[]>([])
const loading = ref(false)
const submitting = ref(false)
const showAddModal = ref(false)
const editMode = ref(false)
const currentEditId = ref<number | null>(null)

const form = reactive({
    name: '',
    description: '',
    website: '',
    notes: '',
    is_active: true
})

const fields = [
    { key: 'name', label: 'Name', sortable: true },
    { key: 'description', label: 'Description' },
    { key: 'is_active', label: 'Status' },
    { key: 'projects_count', label: 'Projects' },
    { key: 'actions', label: 'Actions' }
]

const fetchClients = async () => {
    loading.value = true
    try {
        clients.value = await worklogService.listClients()
    } catch (error) {
        console.error('Failed to fetch clients:', error)
        Swal.fire({
            icon: 'error',
            title: 'Error',
            text: 'Failed to load clients'
        })
    } finally {
        loading.value = false
    }
}

const handleSubmit = async () => {
    submitting.value = true
    try {
        if (editMode.value && currentEditId.value) {
            await worklogService.updateClient(currentEditId.value, form)
        } else {
            await worklogService.createClient(form)
        }

        showAddModal.value = false
        resetForm()

        Swal.fire({
            icon: 'success',
            title: 'Success!',
            text: editMode.value ? 'Client updated successfully' : 'Client created successfully',
            timer: 2000,
            showConfirmButton: false
        })

        fetchClients()
    } catch (error: any) {
        console.error('Failed to save client:', error)
        Swal.fire({
            icon: 'error',
            title: 'Error',
            text: error.message || 'Failed to save client'
        })
    } finally {
        submitting.value = false
    }
}

const editClient = (client: Client) => {
    editMode.value = true
    currentEditId.value = client.id
    form.name = client.name
    form.description = client.description || ''
    form.website = client.website || ''
    form.notes = client.notes || ''
    form.is_active = client.is_active
    showAddModal.value = true
}

const deleteClient = async (client: Client) => {
    const result = await Swal.fire({
        title: 'Are you sure?',
        text: 'This will permanently delete this client and all associated projects',
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#d33',
        cancelButtonColor: '#3085d6',
        confirmButtonText: 'Yes, delete it!'
    })

    if (result.isConfirmed) {
        try {
            await worklogService.deleteClient(client.id)
            Swal.fire({
                icon: 'success',
                title: 'Deleted!',
                text: 'Client has been deleted',
                timer: 2000,
                showConfirmButton: false
            })
            fetchClients()
        } catch (error) {
            console.error('Failed to delete client:', error)
            Swal.fire({
                icon: 'error',
                title: 'Error',
                text: 'Failed to delete client'
            })
        }
    }
}

const viewProjects = (client: Client) => {
    router.push({
        name: 'worklog-projects',
        query: { client: client.id }
    })
}

const resetForm = () => {
    editMode.value = false
    currentEditId.value = null
    form.name = ''
    form.description = ''
    form.website = ''
    form.notes = ''
    form.is_active = true
}

onMounted(() => {
    fetchClients()
})
</script>
