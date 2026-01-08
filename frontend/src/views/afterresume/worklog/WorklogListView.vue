<template>
  <MainLayout>
    <BContainer fluid>
      <PageBreadcrumb title="Work Log" :items="breadcrumbItems" />

      <BRow>
        <BCol cols="12">
          <!-- Quick Add Card -->
          <BCard class="mb-4">
            <BCardBody>
              <h5 class="card-title mb-3">Quick Add Entry</h5>
              <form @submit.prevent="handleQuickAdd">
                <BRow>
                  <BCol md="3">
                    <BFormGroup label="Date" label-for="quick-date">
                      <BFormInput
                        id="quick-date"
                        v-model="quickAddForm.date"
                        type="date"
                        :disabled="quickAddLoading"
                      />
                    </BFormGroup>
                  </BCol>
                  <BCol md="9">
                    <BFormGroup label="What did you accomplish today?" label-for="quick-content">
                      <BFormTextarea
                        id="quick-content"
                        v-model="quickAddForm.content"
                        rows="3"
                        placeholder="Describe your work, achievements, or activities..."
                        :disabled="quickAddLoading"
                        required
                      />
                    </BFormGroup>
                  </BCol>
                </BRow>
                <div class="text-end">
                  <BButton
                    type="submit"
                    variant="primary"
                    :disabled="quickAddLoading || !quickAddForm.content"
                  >
                    <span v-if="quickAddLoading">
                      <span class="spinner-border spinner-border-sm me-2"></span>
                      Adding...
                    </span>
                    <span v-else>
                      <i class="ri-add-line me-1"></i>
                      Add Entry
                    </span>
                  </BButton>
                </div>
              </form>
            </BCardBody>
          </BCard>

          <!-- Filters & Search -->
          <BCard class="mb-4">
            <BCardBody>
              <BRow class="g-3">
                <BCol md="4">
                  <BFormInput
                    v-model="filters.search"
                    placeholder="Search entries..."
                    @input="debouncedSearch"
                  >
                    <template #prepend>
                      <span class="input-group-text">
                        <i class="ri-search-line"></i>
                      </span>
                    </template>
                  </BFormInput>
                </BCol>
                <BCol md="3">
                  <BFormInput
                    v-model="filters.date_from"
                    type="date"
                    placeholder="From date"
                    @change="loadWorklogs"
                  />
                </BCol>
                <BCol md="3">
                  <BFormInput
                    v-model="filters.date_to"
                    type="date"
                    placeholder="To date"
                    @change="loadWorklogs"
                  />
                </BCol>
                <BCol md="2">
                  <BButton variant="secondary" class="w-100" @click="clearFilters">
                    <i class="ri-refresh-line me-1"></i>
                    Clear
                  </BButton>
                </BCol>
              </BRow>
            </BCardBody>
          </BCard>

          <!-- Work Log Entries -->
          <BCard>
            <BCardBody>
              <div class="d-flex justify-content-between align-items-center mb-3">
                <h5 class="card-title mb-0">Your Work Entries</h5>
                <BBadge variant="primary" pill>{{ totalCount }} total</BBadge>
              </div>

              <!-- Loading State -->
              <div v-if="loading" class="text-center py-5">
                <div class="spinner-border text-primary" role="status">
                  <span class="visually-hidden">Loading...</span>
                </div>
              </div>

              <!-- Empty State -->
              <div v-else-if="!worklogs.length" class="text-center py-5">
                <i class="ri-file-list-3-line display-4 text-muted mb-3"></i>
                <p class="text-muted">No work log entries found. Start by adding your first entry above!</p>
              </div>

              <!-- Worklog List -->
              <div v-else class="worklog-list">
                <div
                  v-for="entry in worklogs"
                  :key="entry.id"
                  class="worklog-entry mb-3 p-3 border rounded"
                >
                  <div class="d-flex justify-content-between align-items-start">
                    <div class="flex-grow-1">
                      <div class="d-flex align-items-center mb-2">
                        <h6 class="mb-0 me-3">
                          <i class="ri-calendar-line me-1"></i>
                          {{ formatDate(entry.date) }}
                        </h6>
                        <BBadge v-if="entry.source" variant="info" pill>
                          {{ entry.source }}
                        </BBadge>
                      </div>
                      <p class="mb-2 text-break">{{ entry.content }}</p>
                      <small class="text-muted">
                        <i class="ri-time-line me-1"></i>
                        {{ formatDateTime(entry.created_at) }}
                        <span v-if="entry.attachments && entry.attachments.length > 0" class="ms-3">
                          <i class="ri-attachment-line me-1"></i>
                          {{ entry.attachments.length }} attachment(s)
                        </span>
                      </small>
                    </div>
                    <div class="d-flex gap-2">
                      <BButton
                        size="sm"
                        variant="outline-primary"
                        @click="viewEntry(entry.id!)"
                      >
                        <i class="ri-eye-line"></i>
                      </BButton>
                      <BButton
                        size="sm"
                        variant="outline-danger"
                        @click="confirmDelete(entry)"
                      >
                        <i class="ri-delete-bin-line"></i>
                      </BButton>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Pagination -->
              <div v-if="totalPages > 1" class="mt-4">
                <BPagination
                  v-model="currentPage"
                  :total-rows="totalCount"
                  :per-page="pageSize"
                  align="center"
                  @update:modelValue="loadWorklogs"
                />
              </div>
            </BCardBody>
          </BCard>
        </BCol>
      </BRow>
    </BContainer>
  </MainLayout>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import MainLayout from '@/layouts/main.vue'
import PageBreadcrumb from '@/components/PageBreadcrumb.vue'
import worklogService, { type WorkLog } from '@/services/worklog.service'
import { usePageMeta } from '@/composables/usePageMeta'
import Swal from 'sweetalert2'

usePageMeta('Work Log')

const router = useRouter()

const breadcrumbItems = [
  { text: 'AfterResume', href: '/' },
  { text: 'Work Log', active: true }
]

// State
const worklogs = ref<WorkLog[]>([])
const loading = ref(false)
const quickAddLoading = ref(false)
const currentPage = ref(1)
const pageSize = 20
const totalCount = ref(0)

const totalPages = computed(() => Math.ceil(totalCount.value / pageSize))

// Quick Add Form
const quickAddForm = reactive({
  date: new Date().toISOString().split('T')[0],
  content: ''
})

// Filters
const filters = reactive({
  search: '',
  date_from: '',
  date_to: '',
  source: ''
})

// Methods
const loadWorklogs = async () => {
  loading.value = true
  try {
    const response = await worklogService.list({
      page: currentPage.value,
      search: filters.search || undefined,
      date_from: filters.date_from || undefined,
      date_to: filters.date_to || undefined,
      source: filters.source || undefined
    })
    worklogs.value = response.results
    totalCount.value = response.count
  } catch (error: any) {
    Swal.fire('Error', error.message || 'Failed to load work logs', 'error')
  } finally {
    loading.value = false
  }
}

let searchTimeout: any = null
const debouncedSearch = () => {
  if (searchTimeout) clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    currentPage.value = 1
    loadWorklogs()
  }, 500)
}

const clearFilters = () => {
  filters.search = ''
  filters.date_from = ''
  filters.date_to = ''
  filters.source = ''
  currentPage.value = 1
  loadWorklogs()
}

const handleQuickAdd = async () => {
  if (!quickAddForm.content) return

  quickAddLoading.value = true
  try {
    await worklogService.create({
      date: quickAddForm.date,
      content: quickAddForm.content,
      source: 'manual'
    })

    // Reset form
    quickAddForm.content = ''
    quickAddForm.date = new Date().toISOString().split('T')[0]

    // Reload list
    await loadWorklogs()

    Swal.fire('Success', 'Work log entry added successfully', 'success')
  } catch (error: any) {
    Swal.fire('Error', error.message || 'Failed to add work log entry', 'error')
  } finally {
    quickAddLoading.value = false
  }
}

const viewEntry = (id: number) => {
  router.push(`/worklog/${id}`)
}

const confirmDelete = async (entry: WorkLog) => {
  const result = await Swal.fire({
    title: 'Delete Entry?',
    text: 'This action cannot be undone',
    icon: 'warning',
    showCancelButton: true,
    confirmButtonColor: '#d33',
    cancelButtonColor: '#3085d6',
    confirmButtonText: 'Yes, delete it'
  })

  if (result.isConfirmed) {
    await deleteEntry(entry.id!)
  }
}

const deleteEntry = async (id: number) => {
  try {
    await worklogService.delete(id)
    await loadWorklogs()
    Swal.fire('Deleted!', 'Work log entry has been deleted', 'success')
  } catch (error: any) {
    Swal.fire('Error', error.message || 'Failed to delete work log entry', 'error')
  }
}

const formatDate = (dateStr: string) => {
  return new Date(dateStr).toLocaleDateString('en-US', {
    weekday: 'short',
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  })
}

const formatDateTime = (dateStr: string) => {
  return new Date(dateStr).toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// Lifecycle
onMounted(() => {
  loadWorklogs()
})
</script>

<style scoped>
.worklog-entry {
  transition: all 0.2s ease;
}

.worklog-entry:hover {
  background-color: #f8f9fa;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}
</style>
