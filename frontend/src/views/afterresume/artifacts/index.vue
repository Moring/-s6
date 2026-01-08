<template>
    <MainLayout>
        <BContainer fluid>
            <PageBreadcrumb title="Artifacts & Files" />

            <!-- Upload Section -->
            <BRow class="mb-3">
                <BCol cols="12">
                    <UICard title="Upload Files">
                        <FileUploader
                            @files-uploaded="handleFilesUploaded"
                            accept="image/*,application/pdf,.doc,.docx,.txt"
                            :max-files="5"
                            :max-file-size="10485760"
                        />
                    </UICard>
                </BCol>
            </BRow>

            <!-- Filters -->
            <BRow class="mb-3">
                <BCol cols="12">
                    <UICard>
                        <BRow class="align-items-end">
                            <BCol md="4">
                                <BFormGroup label="Search Files" label-for="search">
                                    <BFormInput
                                        id="search"
                                        v-model="filters.search"
                                        placeholder="Search by filename..."
                                        @input="debouncedSearch"
                                    />
                                </BFormGroup>
                            </BCol>
                            <BCol md="3">
                                <BFormGroup label="File Type" label-for="type">
                                    <BFormSelect
                                        id="type"
                                        v-model="filters.kind"
                                        :options="typeOptions"
                                        @change="fetchArtifacts"
                                    />
                                </BFormGroup>
                            </BCol>
                            <BCol md="3">
                                <BFormGroup label="Sort By" label-for="sort">
                                    <BFormSelect
                                        id="sort"
                                        v-model="filters.sort"
                                        :options="sortOptions"
                                        @change="fetchArtifacts"
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

            <!-- Files List -->
            <BRow>
                <BCol cols="12">
                    <UICard title="Your Files">
                        <div v-if="loading" class="text-center py-5">
                            <div class="spinner-border text-primary" role="status">
                                <span class="visually-hidden">Loading...</span>
                            </div>
                        </div>

                        <div v-else-if="artifacts.length === 0" class="text-center py-5 text-muted">
                            <Icon icon="tabler:file-off" :width="64" :height="64" class="mb-3" />
                            <h5>No files uploaded yet</h5>
                            <p>Upload your first file using the uploader above</p>
                        </div>

                        <div v-else>
                            <div class="table-responsive">
                                <table class="table table-hover">
                                    <thead>
                                        <tr>
                                            <th>Filename</th>
                                            <th>Type</th>
                                            <th>Size</th>
                                            <th>Uploaded</th>
                                            <th>Actions</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <tr v-for="file in artifacts" :key="file.id">
                                            <td>
                                                <div class="d-flex align-items-center">
                                                    <Icon :icon="getFileIcon(file.filename)" class="me-2" :width="24" />
                                                    <span>{{ file.filename }}</span>
                                                </div>
                                            </td>
                                            <td>
                                                <BBadge :variant="getTypeBadge(file.kind)">
                                                    {{ file.kind }}
                                                </BBadge>
                                            </td>
                                            <td>{{ formatBytes(file.size_bytes) }}</td>
                                            <td>{{ formatDate(file.created_at) }}</td>
                                            <td>
                                                <div class="d-flex gap-2">
                                                    <BButton variant="link" size="sm" @click="downloadFile(file)">
                                                        <Icon icon="tabler:download" />
                                                    </BButton>
                                                    <BButton variant="link" size="sm" class="text-danger" @click="deleteFile(file)">
                                                        <Icon icon="tabler:trash" />
                                                    </BButton>
                                                </div>
                                            </td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>

                            <!-- Pagination -->
                            <div v-if="totalPages > 1" class="d-flex justify-content-between align-items-center mt-4">
                                <div class="text-muted">
                                    Showing {{ (currentPage - 1) * pageSize + 1 }} to {{ Math.min(currentPage * pageSize, totalItems) }} of {{ totalItems }} files
                                </div>
                                <BPagination
                                    v-model="currentPage"
                                    :total-rows="totalItems"
                                    :per-page="pageSize"
                                    @update:model-value="fetchArtifacts"
                                />
                            </div>
                        </div>
                    </UICard>
                </BCol>
            </BRow>
        </BContainer>
    </MainLayout>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { Icon } from '@iconify/vue'
import PageBreadcrumb from '@/components/PageBreadcrumb.vue'
import FileUploader from '@/components/FileUploader.vue'
import { usePageMeta } from '@/composables/usePageMeta'
import MainLayout from '@/layouts/MainLayout.vue'
import UICard from '@/components/UICard.vue'
import apiClient from '@/services/api'
import dayjs from 'dayjs'
import Swal from 'sweetalert2'

usePageMeta('Artifacts & Files')

const artifacts = ref<any[]>([])
const loading = ref(false)

const currentPage = ref(1)
const pageSize = ref(20)
const totalItems = ref(0)
const totalPages = ref(0)

const filters = reactive({
    search: '',
    kind: 'all',
    sort: 'recent'
})

const typeOptions = [
    { value: 'all', text: 'All Types' },
    { value: 'resume', text: 'Resume' },
    { value: 'document', text: 'Document' },
    { value: 'image', text: 'Image' }
]

const sortOptions = [
    { value: 'recent', text: 'Most Recent' },
    { value: 'oldest', text: 'Oldest First' },
    { value: 'name_asc', text: 'Name (A-Z)' },
    { value: 'name_desc', text: 'Name (Z-A)' },
    { value: 'size_desc', text: 'Largest First' },
    { value: 'size_asc', text: 'Smallest First' }
]

let searchTimeout: any = null

const debouncedSearch = () => {
    clearTimeout(searchTimeout)
    searchTimeout = setTimeout(() => {
        fetchArtifacts()
    }, 500)
}

const formatDate = (date: string) => {
    return dayjs(date).format('MMM D, YYYY h:mm A')
}

const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}

const getFileIcon = (filename: string) => {
    const ext = filename.split('.').pop()?.toLowerCase()
    switch (ext) {
        case 'pdf':
            return 'tabler:file-type-pdf'
        case 'doc':
        case 'docx':
            return 'tabler:file-type-doc'
        case 'txt':
            return 'tabler:file-type-txt'
        case 'jpg':
        case 'jpeg':
        case 'png':
        case 'gif':
            return 'tabler:photo'
        default:
            return 'tabler:file'
    }
}

const getTypeBadge = (kind: string) => {
    switch (kind) {
        case 'resume':
            return 'primary'
        case 'document':
            return 'info'
        case 'image':
            return 'success'
        default:
            return 'secondary'
    }
}

const resetFilters = () => {
    filters.search = ''
    filters.kind = 'all'
    filters.sort = 'recent'
    fetchArtifacts()
}

const fetchArtifacts = async () => {
    loading.value = true
    try {
        const params: any = {
            page: currentPage.value,
            limit: pageSize.value
        }

        if (filters.search) params.search = filters.search
        if (filters.kind !== 'all') params.kind = filters.kind
        if (filters.sort) params.sort = filters.sort

        const response = await apiClient.get('/api/artifacts/', { params })
        artifacts.value = response.data.results || []
        totalItems.value = response.data.count || 0
        totalPages.value = Math.ceil(totalItems.value / pageSize.value)
    } catch (error) {
        console.error('Failed to fetch artifacts:', error)
        Swal.fire({
            icon: 'error',
            title: 'Error',
            text: 'Failed to load files'
        })
    } finally {
        loading.value = false
    }
}

const handleFilesUploaded = async (files: File[]) => {
    for (const file of files) {
        try {
            const formData = new FormData()
            formData.append('file', file)

            await apiClient.post('/api/artifacts/upload/', formData, {
                headers: {
                    'Content-Type': 'multipart/form-data'
                }
            })
        } catch (error) {
            console.error('Failed to upload file:', error)
            Swal.fire({
                icon: 'error',
                title: 'Error',
                text: `Failed to upload ${file.name}`
            })
        }
    }

    Swal.fire({
        icon: 'success',
        title: 'Success!',
        text: 'Files uploaded successfully',
        timer: 2000,
        showConfirmButton: false
    })

    fetchArtifacts()
}

const downloadFile = (file: any) => {
    // TODO: Implement download from MinIO
    Swal.fire({
        icon: 'info',
        title: 'Coming Soon',
        text: 'File download will be implemented soon'
    })
}

const deleteFile = async (file: any) => {
    const result = await Swal.fire({
        title: 'Are you sure?',
        text: 'This will permanently delete this file',
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#d33',
        cancelButtonColor: '#3085d6',
        confirmButtonText: 'Yes, delete it!'
    })

    if (result.isConfirmed) {
        try {
            await apiClient.delete(`/api/artifacts/${file.id}/`)
            Swal.fire({
                icon: 'success',
                title: 'Deleted!',
                text: 'File has been deleted',
                timer: 2000,
                showConfirmButton: false
            })
            fetchArtifacts()
        } catch (error) {
            console.error('Failed to delete file:', error)
            Swal.fire({
                icon: 'error',
                title: 'Error',
                text: 'Failed to delete file'
            })
        }
    }
}

onMounted(() => {
    fetchArtifacts()
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
