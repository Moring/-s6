<template>
    <BModal
        :model-value="modelValue"
        :title="isEdit ? 'Edit Worklog Entry' : 'Add Worklog Entry'"
        size="xl"
        @update:model-value="$emit('update:modelValue', $event)"
        @hidden="resetForm"
    >
        <BForm @submit.prevent="handleSubmit">
            <!-- Basic Information -->
            <BRow>
                <BCol md="4">
                    <BFormGroup label="Date *" label-for="occurred_on" class="mb-3">
                        <BFormInput
                            id="occurred_on"
                            v-model="form.occurred_on"
                            type="date"
                            required
                        />
                    </BFormGroup>
                </BCol>
                <BCol md="4">
                    <BFormGroup label="Work Type *" label-for="work_type" class="mb-3">
                        <BFormSelect
                            id="work_type"
                            v-model="form.work_type"
                            :options="workTypeOptions"
                            required
                        />
                    </BFormGroup>
                </BCol>
                <BCol md="4">
                    <BFormGroup label="Status" label-for="status" class="mb-3">
                        <BFormSelect
                            id="status"
                            v-model="form.status"
                            :options="statusOptions"
                        />
                    </BFormGroup>
                </BCol>
            </BRow>

            <BFormGroup label="Title (Optional)" label-for="title" class="mb-3">
                <BFormInput
                    id="title"
                    v-model="form.title"
                    placeholder="Brief title for this entry..."
                />
            </BFormGroup>

            <!-- Organizational Context -->
            <BCard class="mb-3" border-variant="light">
                <BCardHeader class="bg-light">
                    <h6 class="mb-0">
                        <Icon icon="tabler:building" class="me-2" />
                        Organizational Context (Optional)
                    </h6>
                </BCardHeader>
                <BCardBody>
                    <BRow>
                        <BCol md="6">
                            <BFormGroup label="Client/Employer" label-for="client">
                                <BFormSelect
                                    id="client"
                                    v-model="form.client"
                                    :options="clientOptions"
                                    @change="onClientChange"
                                />
                            </BFormGroup>
                        </BCol>
                        <BCol md="6">
                            <BFormGroup label="Project" label-for="project">
                                <BFormSelect
                                    id="project"
                                    v-model="form.project"
                                    :options="projectOptions"
                                    :disabled="!form.client"
                                />
                            </BFormGroup>
                        </BCol>
                    </BRow>

                    <!-- Agile Hierarchy (Collapsible) -->
                    <BButton
                        v-b-toggle.agile-collapse
                        variant="link"
                        size="sm"
                        class="p-0 text-decoration-none mb-2"
                    >
                        <Icon icon="tabler:chevron-down" class="me-1" />
                        Agile Tracking (Epic, Feature, Story, Task, Sprint)
                    </BButton>
                    <BCollapse id="agile-collapse">
                        <BRow>
                            <BCol md="4">
                                <BFormGroup label="Sprint" label-for="sprint" class="mb-2">
                                    <BFormSelect
                                        id="sprint"
                                        v-model="form.sprint"
                                        :options="sprintOptions"
                                        :disabled="!form.project"
                                    />
                                </BFormGroup>
                            </BCol>
                            <BCol md="4">
                                <BFormGroup label="Epic" label-for="epic" class="mb-2">
                                    <BFormSelect
                                        id="epic"
                                        v-model="form.epic"
                                        :options="epicOptions"
                                        :disabled="!form.project"
                                        @change="onEpicChange"
                                    />
                                </BFormGroup>
                            </BCol>
                            <BCol md="4">
                                <BFormGroup label="Feature" label-for="feature" class="mb-2">
                                    <BFormSelect
                                        id="feature"
                                        v-model="form.feature"
                                        :options="featureOptions"
                                        :disabled="!form.epic"
                                        @change="onFeatureChange"
                                    />
                                </BFormGroup>
                            </BCol>
                        </BRow>
                        <BRow>
                            <BCol md="6">
                                <BFormGroup label="Story" label-for="story" class="mb-2">
                                    <BFormSelect
                                        id="story"
                                        v-model="form.story"
                                        :options="storyOptions"
                                        :disabled="!form.feature"
                                        @change="onStoryChange"
                                    />
                                </BFormGroup>
                            </BCol>
                            <BCol md="6">
                                <BFormGroup label="Task" label-for="task" class="mb-2">
                                    <BFormSelect
                                        id="task"
                                        v-model="form.task"
                                        :options="taskOptions"
                                        :disabled="!form.story"
                                    />
                                </BFormGroup>
                            </BCol>
                        </BRow>
                    </BCollapse>
                </BCardBody>
            </BCard>

            <!-- Content -->
            <BFormGroup label="What did you work on? *" label-for="content" class="mb-3">
                <BFormTextarea
                    id="content"
                    v-model="form.content"
                    placeholder="Describe your work in detail..."
                    rows="4"
                    required
                />
                <small class="text-muted">Raw notes are fine - AI can help enhance later</small>
            </BFormGroup>

            <BRow>
                <BCol md="6">
                    <BFormGroup label="Outcome (What was accomplished)" label-for="outcome" class="mb-3">
                        <BFormTextarea
                            id="outcome"
                            v-model="form.outcome"
                            placeholder="What was delivered or achieved..."
                            rows="3"
                        />
                    </BFormGroup>
                </BCol>
                <BCol md="6">
                    <BFormGroup label="Impact (Why it mattered)" label-for="impact" class="mb-3">
                        <BFormTextarea
                            id="impact"
                            v-model="form.impact"
                            placeholder="Customer impact, metrics, risk reduction..."
                            rows="3"
                        />
                    </BFormGroup>
                </BCol>
            </BRow>

            <BFormGroup label="Next Steps" label-for="next_steps" class="mb-3">
                <BFormTextarea
                    id="next_steps"
                    v-model="form.next_steps"
                    placeholder="Follow-ups, blockers, future work..."
                    rows="2"
                />
            </BFormGroup>

            <!-- Time Tracking -->
            <BRow>
                <BCol md="6">
                    <BFormGroup label="Effort (hours)" label-for="hours" class="mb-3">
                        <BFormInput
                            id="hours"
                            v-model.number="hoursInput"
                            type="number"
                            step="0.25"
                            min="0"
                            placeholder="Optional: 1.5, 2.0, etc."
                        />
                    </BFormGroup>
                </BCol>
                <BCol md="6">
                    <BFormGroup class="mb-3">
                        <label>&nbsp;</label>
                        <BFormCheckbox v-model="form.is_billable">
                            Billable Time
                        </BFormCheckbox>
                    </BFormGroup>
                </BCol>
            </BRow>

            <!-- Tags -->
            <BFormGroup label="Tags (comma-separated)" label-for="tags" class="mb-3">
                <BFormInput
                    id="tags"
                    v-model="tagsInput"
                    placeholder="python, kubernetes, api-design, troubleshooting..."
                />
                <small class="text-muted">Skills, technologies, tools, methods</small>
            </BFormGroup>
        </BForm>

        <template #footer>
            <BButton variant="light" @click="$emit('update:modelValue', false)">Cancel</BButton>
            <BButton variant="primary" @click="handleSubmit" :disabled="submitting">
                <span v-if="submitting">
                    <span class="spinner-border spinner-border-sm me-1"></span>
                    Saving...
                </span>
                <span v-else>{{ isEdit ? 'Update' : 'Save' }}</span>
            </BButton>
        </template>
    </BModal>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue'
import { Icon } from '@iconify/vue'
import { worklogService, type WorkLog, type Client, type Project } from '@/services/worklog.service'
import Swal from 'sweetalert2'

const props = defineProps<{
    modelValue: boolean
    entry: WorkLog | null
    clients: Client[]
    projects: Project[]
}>()

const emit = defineEmits(['update:modelValue', 'saved'])

const submitting = ref(false)
const epics = ref<any[]>([])
const features = ref<any[]>([])
const stories = ref<any[]>([])
const tasks = ref<any[]>([])
const sprints = ref<any[]>([])

const form = reactive({
    occurred_on: '',
    title: '',
    client: null as number | null,
    project: null as number | null,
    epic: null as number | null,
    feature: null as number | null,
    story: null as number | null,
    task: null as number | null,
    sprint: null as number | null,
    work_type: 'delivery' as any,
    status: 'draft' as any,
    content: '',
    outcome: '',
    impact: '',
    next_steps: '',
    effort_minutes: null as number | null,
    is_billable: false,
    tags: [] as string[],
    source: 'manual' as any,
    enrichment_status: 'pending' as any
})

const hoursInput = ref<number | null>(null)
const tagsInput = ref('')

const isEdit = computed(() => !!props.entry)

const workTypeOptions = [
    { value: 'delivery', text: 'Delivery' },
    { value: 'planning', text: 'Planning' },
    { value: 'incident', text: 'Incident Response' },
    { value: 'support', text: 'Support' },
    { value: 'learning', text: 'Learning/Training' },
    { value: 'other', text: 'Other' }
]

const statusOptions = [
    { value: 'draft', text: 'Draft' },
    { value: 'ready', text: 'Ready for Review' },
    { value: 'final', text: 'Final' },
    { value: 'archived', text: 'Archived' }
]

const clientOptions = computed(() => {
    return [
        { value: null, text: '-- Select Client --' },
        ...props.clients.map(c => ({ value: c.id, text: c.name }))
    ]
})

const projectOptions = computed(() => {
    if (!form.client) {
        return [{ value: null, text: '-- Select Client First --' }]
    }
    
    const filtered = props.projects.filter(p => p.client === form.client)
    return [
        { value: null, text: '-- Select Project --' },
        ...filtered.map(p => ({ value: p.id, text: p.name }))
    ]
})

const epicOptions = computed(() => {
    return [
        { value: null, text: '-- None --' },
        ...epics.value.map(e => ({ value: e.id, text: e.name }))
    ]
})

const featureOptions = computed(() => {
    return [
        { value: null, text: '-- None --' },
        ...features.value.map(f => ({ value: f.id, text: f.name }))
    ]
})

const storyOptions = computed(() => {
    return [
        { value: null, text: '-- None --' },
        ...stories.value.map(s => ({ value: s.id, text: s.name }))
    ]
})

const taskOptions = computed(() => {
    return [
        { value: null, text: '-- None --' },
        ...tasks.value.map(t => ({ value: t.id, text: t.name }))
    ]
})

const sprintOptions = computed(() => {
    return [
        { value: null, text: '-- None --' },
        ...sprints.value.map(s => ({ value: s.id, text: s.name }))
    ]
})

const onClientChange = () => {
    form.project = null
    form.epic = null
    form.feature = null
    form.story = null
    form.task = null
    form.sprint = null
    epics.value = []
    features.value = []
    stories.value = []
    tasks.value = []
    sprints.value = []
}

const onEpicChange = async () => {
    form.feature = null
    form.story = null
    form.task = null
    features.value = []
    stories.value = []
    tasks.value = []
    
    if (form.epic) {
        features.value = await worklogService.listFeatures(form.epic)
    }
}

const onFeatureChange = async () => {
    form.story = null
    form.task = null
    stories.value = []
    tasks.value = []
    
    if (form.feature) {
        stories.value = await worklogService.listStories(form.feature)
    }
}

const onStoryChange = async () => {
    form.task = null
    tasks.value = []
    
    if (form.story) {
        tasks.value = await worklogService.listTasks(form.story)
    }
}

watch(() => form.project, async (newProject) => {
    if (newProject) {
        epics.value = await worklogService.listEpics(newProject)
        sprints.value = await worklogService.listSprints(newProject)
    }
})

watch(() => props.entry, (entry) => {
    if (entry) {
        populateForm(entry)
    } else {
        resetForm()
    }
}, { immediate: true })

const populateForm = (entry: WorkLog) => {
    form.occurred_on = entry.occurred_on
    form.title = entry.title || ''
    form.client = entry.client || null
    form.project = entry.project || null
    form.epic = entry.epic || null
    form.feature = entry.feature || null
    form.story = entry.story || null
    form.task = entry.task || null
    form.sprint = entry.sprint || null
    form.work_type = entry.work_type
    form.status = entry.status
    form.content = entry.content
    form.outcome = entry.outcome || ''
    form.impact = entry.impact || ''
    form.next_steps = entry.next_steps || ''
    form.effort_minutes = entry.effort_minutes || null
    form.is_billable = entry.is_billable || false
    form.tags = entry.tags || []
    
    if (entry.effort_minutes) {
        hoursInput.value = entry.effort_minutes / 60
    }
    
    tagsInput.value = (entry.tags || []).join(', ')
}

const resetForm = () => {
    form.occurred_on = new Date().toISOString().split('T')[0]
    form.title = ''
    form.client = null
    form.project = null
    form.epic = null
    form.feature = null
    form.story = null
    form.task = null
    form.sprint = null
    form.work_type = 'delivery'
    form.status = 'draft'
    form.content = ''
    form.outcome = ''
    form.impact = ''
    form.next_steps = ''
    form.effort_minutes = null
    form.is_billable = false
    form.tags = []
    hoursInput.value = null
    tagsInput.value = ''
}

const handleSubmit = async () => {
    submitting.value = true
    try {
        // Process hours to minutes
        if (hoursInput.value !== null && hoursInput.value > 0) {
            form.effort_minutes = Math.round(hoursInput.value * 60)
        } else {
            form.effort_minutes = null
        }
        
        // Process tags
        form.tags = tagsInput.value
            .split(',')
            .map(t => t.trim())
            .filter(t => t.length > 0)

        if (isEdit.value && props.entry?.id) {
            await worklogService.update(props.entry.id, form)
        } else {
            await worklogService.create(form)
        }

        Swal.fire({
            icon: 'success',
            title: 'Success!',
            text: isEdit.value ? 'Entry updated successfully' : 'Entry created successfully',
            timer: 2000,
            showConfirmButton: false
        })

        emit('saved')
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
</script>
