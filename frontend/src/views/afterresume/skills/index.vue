<template>
    <MainLayout>
        <BContainer fluid>
            <PageBreadcrumb title="Skills Library" />

            <!-- AI Assistant -->
            <BRow class="mb-3">
                <BCol cols="12">
                    <AIChatInput 
                        placeholder="Ask about your skills, request analysis, or get career advice..."
                        context="skills"
                    />
                </BCol>
            </BRow>

            <!-- Header Actions -->
            <BRow class="mb-3">
                <BCol cols="12">
                    <UICard>
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <h5 class="mb-1">Your Skills Portfolio</h5>
                                <p class="text-muted mb-0">Evidence-based skills extracted from your work</p>
                            </div>
                            <div class="d-flex gap-2">
                                <BButton variant="outline-primary" @click="handleRecompute" :disabled="recomputing">
                                    <Icon icon="tabler:refresh" class="me-1" />
                                    <span v-if="recomputing">Recomputing...</span>
                                    <span v-else>Recompute Skills</span>
                                </BButton>
                                <BButton variant="primary" @click="showExportMenu = !showExportMenu">
                                    <Icon icon="tabler:download" class="me-1" />
                                    Export
                                </BButton>
                            </div>
                        </div>
                        
                        <!-- Export Dropdown -->
                        <div v-if="showExportMenu" class="mt-3 text-end">
                            <BButton variant="light" size="sm" class="me-2" @click="exportSkills('csv')">
                                Export CSV
                            </BButton>
                            <BButton variant="light" size="sm" @click="exportSkills('json')">
                                Export JSON
                            </BButton>
                        </div>
                    </UICard>
                </BCol>
            </BRow>

            <!-- Filters -->
            <BRow class="mb-3">
                <BCol cols="12">
                    <UICard>
                        <BRow class="align-items-end">
                            <BCol md="4">
                                <BFormGroup label="Search Skills" label-for="search">
                                    <BFormInput
                                        id="search"
                                        v-model="filters.search"
                                        placeholder="Search by skill name..."
                                        @input="debouncedSearch"
                                    />
                                </BFormGroup>
                            </BCol>
                            <BCol md="3">
                                <BFormGroup label="Confidence Level" label-for="confidence">
                                    <BFormSelect
                                        id="confidence"
                                        v-model="filters.confidence"
                                        :options="confidenceOptions"
                                        @change="fetchSkills"
                                    />
                                </BFormGroup>
                            </BCol>
                            <BCol md="3">
                                <BFormGroup label="Sort By" label-for="sort">
                                    <BFormSelect
                                        id="sort"
                                        v-model="filters.sort"
                                        :options="sortOptions"
                                        @change="fetchSkills"
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

            <!-- Skills List -->
            <BRow>
                <BCol cols="12">
                    <UICard title="Skills">
                        <div v-if="loading" class="text-center py-5">
                            <div class="spinner-border text-primary" role="status">
                                <span class="visually-hidden">Loading...</span>
                            </div>
                        </div>

                        <div v-else-if="skills.length === 0" class="text-center py-5 text-muted">
                            <Icon icon="tabler:certificate-off" :width="64" :height="64" class="mb-3" />
                            <h5>No skills found</h5>
                            <p>Skills will be automatically extracted from your worklog entries and documents</p>
                            <BButton variant="primary" @click="handleRecompute">
                                <Icon icon="tabler:refresh" class="me-1" />
                                Extract Skills Now
                            </BButton>
                        </div>

                        <div v-else>
                            <div v-for="skill in skills" :key="skill.id" class="skill-item border-bottom py-3">
                                <div class="d-flex justify-content-between align-items-start mb-2">
                                    <div class="flex-grow-1">
                                        <h6 class="mb-1">
                                            {{ skill.name }}
                                            <BBadge v-if="skill.name !== skill.normalized" variant="light" class="ms-2">
                                                → {{ skill.normalized }}
                                            </BBadge>
                                        </h6>
                                        <div class="d-flex align-items-center gap-3">
                                            <div>
                                                <small class="text-muted">Confidence:</small>
                                                <BBadge :variant="getConfidenceBadge(skill.confidence)" class="ms-1">
                                                    {{ (skill.confidence * 100).toFixed(0) }}%
                                                </BBadge>
                                            </div>
                                            <div v-if="skill.level">
                                                <small class="text-muted">Level:</small>
                                                <BBadge variant="info" class="ms-1">{{ skill.level }}</BBadge>
                                            </div>
                                            <div>
                                                <small class="text-muted">Evidence:</small>
                                                <BBadge variant="secondary" class="ms-1">{{ skill.evidence_count }}</BBadge>
                                            </div>
                                        </div>
                                        <div v-if="skill.metadata && Object.keys(skill.metadata).length > 0" class="mt-2">
                                            <small class="text-muted">
                                                Updated: {{ formatDate(skill.updated_at) }}
                                            </small>
                                        </div>
                                    </div>
                                    <div class="d-flex gap-2">
                                        <BButton variant="link" size="sm" @click="viewEvidence(skill)">
                                            <Icon icon="tabler:list-details" />
                                            View Evidence
                                        </BButton>
                                    </div>
                                </div>
                            </div>

                            <!-- Pagination -->
                            <div v-if="totalPages > 1" class="d-flex justify-content-between align-items-center mt-4">
                                <div class="text-muted">
                                    Showing {{ (currentPage - 1) * pageSize + 1 }} to {{ Math.min(currentPage * pageSize, totalItems) }} of {{ totalItems }} skills
                                </div>
                                <BPagination
                                    v-model="currentPage"
                                    :total-rows="totalItems"
                                    :per-page="pageSize"
                                    @update:model-value="fetchSkills"
                                />
                            </div>
                        </div>
                    </UICard>
                </BCol>
            </BRow>
        </BContainer>

        <!-- Evidence Modal -->
        <BModal
            v-model="showEvidenceModal"
            :title="`Evidence for: ${selectedSkill?.name}`"
            size="lg"
        >
            <div v-if="loadingEvidence" class="text-center py-5">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading evidence...</span>
                </div>
            </div>

            <div v-else-if="evidence.length === 0" class="text-center py-5 text-muted">
                <p>No evidence found for this skill</p>
            </div>

            <div v-else>
                <div v-for="(item, index) in evidence" :key="item.id" class="evidence-item mb-3 p-3 border rounded">
                    <div class="d-flex justify-content-between align-items-start mb-2">
                        <div>
                            <BBadge :variant="getSourceBadge(item.source_type)">
                                {{ item.source_type }}
                            </BBadge>
                            <small class="text-muted ms-2">Weight: {{ item.weight }}</small>
                        </div>
                        <small class="text-muted">{{ formatDate(item.created_at) }}</small>
                    </div>
                    <div v-if="item.excerpt" class="mt-2">
                        <p class="mb-0 text-muted small">{{ item.excerpt }}</p>
                    </div>
                </div>
            </div>

            <template #footer>
                <BButton variant="light" @click="showEvidenceModal = false">Close</BButton>
            </template>
        </BModal>
    </MainLayout>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { Icon } from '@iconify/vue'
import PageBreadcrumb from '@/components/PageBreadcrumb.vue'
import AIChatInput from '@/components/AIChatInput.vue'
import { usePageMeta } from '@/composables/usePageMeta'
import MainLayout from '@/layouts/MainLayout.vue'
import UICard from '@/components/UICard.vue'
import { skillService } from '@/services/skill.service'
import dayjs from 'dayjs'
import Swal from 'sweetalert2'

usePageMeta('Skills Library')

const skills = ref<any[]>([])
const evidence = ref<any[]>([])
const selectedSkill = ref<any>(null)
const loading = ref(false)
const loadingEvidence = ref(false)
const recomputing = ref(false)
const showEvidenceModal = ref(false)
const showExportMenu = ref(false)

const currentPage = ref(1)
const pageSize = ref(20)
const totalItems = ref(0)
const totalPages = ref(0)

const filters = reactive({
    search: '',
    confidence: 'all',
    sort: 'confidence_desc'
})

const confidenceOptions = [
    { value: 'all', text: 'All Levels' },
    { value: 'high', text: 'High (80%+)' },
    { value: 'medium', text: 'Medium (60-80%)' },
    { value: 'low', text: 'Low (<60%)' }
]

const sortOptions = [
    { value: 'confidence_desc', text: 'Confidence (High to Low)' },
    { value: 'confidence_asc', text: 'Confidence (Low to High)' },
    { value: 'name_asc', text: 'Name (A-Z)' },
    { value: 'name_desc', text: 'Name (Z-A)' },
    { value: 'evidence_desc', text: 'Most Evidence' },
    { value: 'recent', text: 'Recently Updated' }
]

let searchTimeout: any = null

const debouncedSearch = () => {
    clearTimeout(searchTimeout)
    searchTimeout = setTimeout(() => {
        fetchSkills()
    }, 500)
}

const formatDate = (date: string) => {
    return dayjs(date).format('MMM D, YYYY')
}

const getConfidenceBadge = (confidence: number) => {
    if (confidence >= 0.8) return 'success'
    if (confidence >= 0.6) return 'info'
    if (confidence >= 0.4) return 'warning'
    return 'light'
}

const getSourceBadge = (sourceType: string) => {
    switch (sourceType) {
        case 'worklog_entry':
            return 'primary'
        case 'document':
            return 'info'
        case 'attachment':
            return 'secondary'
        default:
            return 'light'
    }
}

const resetFilters = () => {
    filters.search = ''
    filters.confidence = 'all'
    filters.sort = 'confidence_desc'
    fetchSkills()
}

const fetchSkills = async () => {
    loading.value = true
    try {
        const params: any = {
            page: currentPage.value,
            limit: pageSize.value
        }

        if (filters.search) params.search = filters.search
        if (filters.confidence !== 'all') params.confidence = filters.confidence
        if (filters.sort) params.sort = filters.sort

        const data = await skillService.listSkills(params)
        skills.value = data.results || []
        totalItems.value = data.count || 0
        totalPages.value = Math.ceil(totalItems.value / pageSize.value)
    } catch (error) {
        console.error('Failed to fetch skills:', error)
        Swal.fire({
            icon: 'error',
            title: 'Error',
            text: 'Failed to load skills'
        })
    } finally {
        loading.value = false
    }
}

const handleRecompute = async () => {
    const result = await Swal.fire({
        title: 'Recompute Skills?',
        text: 'This will extract skills from your worklog entries and documents. This may take a few moments.',
        icon: 'question',
        showCancelButton: true,
        confirmButtonText: 'Yes, recompute',
        cancelButtonText: 'Cancel'
    })

    if (result.isConfirmed) {
        recomputing.value = true
        try {
            await skillService.recomputeSkills()
            Swal.fire({
                icon: 'success',
                title: 'Processing',
                text: 'Skills extraction job has been queued. This may take a few minutes.',
                timer: 3000
            })
            
            // Refresh after a delay
            setTimeout(() => {
                fetchSkills()
            }, 5000)
        } catch (error) {
            console.error('Failed to recompute skills:', error)
            Swal.fire({
                icon: 'error',
                title: 'Error',
                text: 'Failed to start skills extraction'
            })
        } finally {
            recomputing.value = false
        }
    }
}

const viewEvidence = async (skill: any) => {
    selectedSkill.value = skill
    showEvidenceModal.value = true
    loadingEvidence.value = true
    
    try {
        const data = await skillService.getSkillEvidence(skill.id)
        evidence.value = data.results || []
    } catch (error) {
        console.error('Failed to fetch evidence:', error)
        Swal.fire({
            icon: 'error',
            title: 'Error',
            text: 'Failed to load evidence'
        })
    } finally {
        loadingEvidence.value = false
    }
}

const exportSkills = async (format: 'csv' | 'json') => {
    try {
        const data = await skillService.exportSkills(format)
        
        // Create download link
        const blob = new Blob([data], { 
            type: format === 'csv' ? 'text/csv' : 'application/json' 
        })
        const url = window.URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = url
        link.download = `skills_export_${dayjs().format('YYYY-MM-DD')}.${format}`
        link.click()
        window.URL.revokeObjectURL(url)
        
        showExportMenu.value = false
        
        Swal.fire({
            icon: 'success',
            title: 'Exported!',
            text: `Skills exported as ${format.toUpperCase()}`,
            timer: 2000,
            showConfirmButton: false
        })
    } catch (error) {
        console.error('Failed to export skills:', error)
        Swal.fire({
            icon: 'error',
            title: 'Error',
            text: 'Failed to export skills'
        })
    }
}

onMounted(() => {
    fetchSkills()
})
</script>

<style scoped>
.skill-item {
    transition: background-color 0.2s;
}

.skill-item:hover {
    background-color: rgba(0, 0, 0, 0.02);
}

.skill-item:last-child {
    border-bottom: none !important;
}

.evidence-item {
    background-color: rgba(0, 0, 0, 0.02);
}
</style>
