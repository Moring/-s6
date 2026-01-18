<template>
    <BModal
        :model-value="modelValue"
        title="Worklog Entry Details"
        size="xl"
        @update:model-value="$emit('update:modelValue', $event)"
    >
        <div v-if="entry">
            <!-- Header -->
            <div class="d-flex justify-content-between align-items-start mb-4">
                <div>
                    <h4 class="mb-2">{{ entry.title || 'Worklog Entry' }}</h4>
                    <div class="d-flex gap-2 align-items-center">
                        <Icon icon="tabler:calendar" />
                        <span class="text-muted">{{ formatDate(entry.occurred_on) }}</span>
                        <BBadge :variant="(statusVariant(entry.status) as any)">{{ entry.status }}</BBadge>
                        <BBadge variant="secondary">{{ entry.work_type }}</BBadge>
                        <BBadge v-if="entry.is_billable" variant="success">Billable</BBadge>
                    </div>
                </div>
                <div class="d-flex gap-2">
                    <BButton variant="outline-primary" size="sm" @click="$emit('edit', entry)">
                        <Icon icon="tabler:edit" class="me-1" />
                        Edit
                    </BButton>
                    <BButton variant="outline-danger" size="sm" @click="$emit('delete', entry)">
                        <Icon icon="tabler:trash" class="me-1" />
                        Delete
                    </BButton>
                </div>
            </div>

            <!-- Context -->
            <BCard v-if="entry.client_name || entry.project_name" class="mb-3" border-variant="light">
                <BCardHeader class="bg-light">
                    <h6 class="mb-0">
                        <Icon icon="tabler:building" class="me-2" />
                        Context
                    </h6>
                </BCardHeader>
                <BCardBody>
                    <BRow>
                        <BCol md="6" v-if="entry.client_name">
                            <strong>Client:</strong> {{ entry.client_name }}
                        </BCol>
                        <BCol md="6" v-if="entry.project_name">
                            <strong>Project:</strong> {{ entry.project_name }}
                        </BCol>
                    </BRow>
                    <BRow v-if="entry.epic_name || entry.sprint_name" class="mt-2">
                        <BCol md="6" v-if="entry.epic_name">
                            <small><strong>Epic:</strong> {{ entry.epic_name }}</small>
                        </BCol>
                        <BCol md="6" v-if="entry.feature_name">
                            <small><strong>Feature:</strong> {{ entry.feature_name }}</small>
                        </BCol>
                    </BRow>
                    <BRow v-if="entry.story_name || entry.task_name" class="mt-1">
                        <BCol md="6" v-if="entry.story_name">
                            <small><strong>Story:</strong> {{ entry.story_name }}</small>
                        </BCol>
                        <BCol md="6" v-if="entry.task_name">
                            <small><strong>Task:</strong> {{ entry.task_name }}</small>
                        </BCol>
                    </BRow>
                    <BRow v-if="entry.sprint_name" class="mt-1">
                        <BCol cols="12">
                            <small><strong>Sprint:</strong> {{ entry.sprint_name }}</small>
                        </BCol>
                    </BRow>
                </BCardBody>
            </BCard>

            <!-- Content -->
            <BCard class="mb-3">
                <BCardHeader class="bg-light">
                    <h6 class="mb-0">What You Worked On</h6>
                </BCardHeader>
                <BCardBody>
                    <p class="mb-0" style="white-space: pre-wrap;">{{ entry.content }}</p>
                </BCardBody>
            </BCard>

            <!-- Outcome & Impact -->
            <BRow v-if="entry.outcome || entry.impact">
                <BCol md="6" v-if="entry.outcome">
                    <BCard class="mb-3">
                        <BCardHeader class="bg-light">
                            <h6 class="mb-0">Outcome</h6>
                        </BCardHeader>
                        <BCardBody>
                            <p class="mb-0" style="white-space: pre-wrap;">{{ entry.outcome }}</p>
                        </BCardBody>
                    </BCard>
                </BCol>
                <BCol md="6" v-if="entry.impact">
                    <BCard class="mb-3">
                        <BCardHeader class="bg-light">
                            <h6 class="mb-0">Impact</h6>
                        </BCardHeader>
                        <BCardBody>
                            <p class="mb-0" style="white-space: pre-wrap;">{{ entry.impact }}</p>
                        </BCardBody>
                    </BCard>
                </BCol>
            </BRow>

            <!-- Next Steps -->
            <BCard v-if="entry.next_steps" class="mb-3">
                <BCardHeader class="bg-light">
                    <h6 class="mb-0">Next Steps</h6>
                </BCardHeader>
                <BCardBody>
                    <p class="mb-0" style="white-space: pre-wrap;">{{ entry.next_steps }}</p>
                </BCardBody>
            </BCard>

            <!-- Time & Tags -->
            <BRow>
                <BCol md="6" v-if="entry.effort_minutes">
                    <BCard class="mb-3">
                        <BCardBody>
                            <Icon icon="tabler:clock" class="me-2" />
                            <strong>Time Spent:</strong> {{ formatHours(entry.effort_minutes) }}
                        </BCardBody>
                    </BCard>
                </BCol>
                <BCol :md="entry.effort_minutes ? 6 : 12" v-if="entry.tags && entry.tags.length > 0">
                    <BCard class="mb-3">
                        <BCardBody>
                            <Icon icon="tabler:tags" class="me-2" />
                            <strong>Tags:</strong>
                            <div class="mt-2">
                                <BBadge v-for="tag in entry.tags" :key="tag" variant="light" class="me-1">
                                    {{ tag }}
                                </BBadge>
                            </div>
                        </BCardBody>
                    </BCard>
                </BCol>
            </BRow>

            <!-- Attachments -->
            <BCard v-if="entry.attachments && entry.attachments.length > 0" class="mb-3">
                <BCardHeader class="bg-light">
                    <h6 class="mb-0">
                        <Icon icon="tabler:paperclip" class="me-2" />
                        Attachments ({{ entry.attachments.length }})
                    </h6>
                </BCardHeader>
                <BCardBody>
                    <BListGroup>
                        <BListGroupItem v-for="att in entry.attachments" :key="att.id" class="d-flex justify-content-between align-items-center">
                            <div>
                                <Icon icon="tabler:file" class="me-2" />
                                <strong>{{ att.filename }}</strong>
                                <div v-if="att.description" class="text-muted small mt-1">{{ att.description }}</div>
                            </div>
                            <BBadge variant="info">{{ formatBytes(att.size_bytes) }}</BBadge>
                        </BListGroupItem>
                    </BListGroup>
                </BCardBody>
            </BCard>

            <!-- Skill Signals (if enriched) -->
            <BCard v-if="entry.skill_signals && entry.skill_signals.length > 0" class="mb-3">
                <BCardHeader class="bg-light">
                    <h6 class="mb-0">
                        <Icon icon="tabler:sparkles" class="me-2" />
                        Identified Skills
                    </h6>
                </BCardHeader>
                <BCardBody>
                    <div class="d-flex flex-wrap gap-2">
                        <BBadge 
                            v-for="signal in entry.skill_signals" 
                            :key="signal.id"
                            :variant="(skillSignalVariant(signal.status) as any)"
                            class="py-2 px-3"
                        >
                            {{ signal.name }}
                            <small v-if="signal.confidence" class="ms-1">({{ Math.round(signal.confidence * 100) }}%)</small>
                        </BBadge>
                    </div>
                </BCardBody>
            </BCard>

            <!-- AI Summary -->
            <BCard v-if="entry.ai_summary" class="mb-3">
                <BCardHeader class="bg-light">
                    <h6 class="mb-0">
                        <Icon icon="tabler:robot" class="me-2" />
                        AI Summary
                    </h6>
                </BCardHeader>
                <BCardBody>
                    <p class="mb-0" style="white-space: pre-wrap;">{{ entry.ai_summary }}</p>
                </BCardBody>
            </BCard>

            <!-- Bullets (if any) -->
            <BCard v-if="entry.bullets && entry.bullets.length > 0" class="mb-3">
                <BCardHeader class="bg-light">
                    <h6 class="mb-0">
                        <Icon icon="tabler:list" class="me-2" />
                        Generated Bullets
                    </h6>
                </BCardHeader>
                <BCardBody>
                    <BListGroup>
                        <BListGroupItem 
                            v-for="bullet in entry.bullets" 
                            :key="bullet.id"
                            class="d-flex justify-content-between align-items-start"
                        >
                            <div class="flex-grow-1">
                                <BBadge :variant="(bulletKindVariant(bullet.kind) as any)" class="me-2">
                                    {{ bullet.kind }}
                                </BBadge>
                                <span>{{ bullet.text }}</span>
                                <BBadge v-if="bullet.is_ai_generated" variant="info" class="ms-2">
                                    <Icon icon="tabler:robot" width="12" />
                                    AI
                                </BBadge>
                            </div>
                            <BFormCheckbox v-if="!readOnly" v-model="bullet.is_selected" disabled>
                                Use
                            </BFormCheckbox>
                        </BListGroupItem>
                    </BListGroup>
                </BCardBody>
            </BCard>

            <!-- Metadata -->
            <BCard class="mb-3" border-variant="light">
                <BCardBody>
                    <small class="text-muted">
                        <Icon icon="tabler:info-circle" class="me-1" />
                        Created: {{ formatDateTime(entry.created_at) }}
                        <span v-if="entry.updated_at !== entry.created_at">
                            | Updated: {{ formatDateTime(entry.updated_at) }}
                        </span>
                        | Source: {{ entry.source }}
                        | Enrichment: {{ entry.enrichment_status }}
                    </small>
                </BCardBody>
            </BCard>
        </div>

        <template #footer>
            <BButton variant="light" @click="$emit('update:modelValue', false)">Close</BButton>
        </template>
    </BModal>
</template>

<script setup lang="ts">
import { Icon } from '@iconify/vue'
import type { WorkLog } from '@/services/worklog.service'
import dayjs from 'dayjs'

defineProps<{
    modelValue: boolean
    entry: WorkLog | null
    readOnly?: boolean
}>()

defineEmits(['update:modelValue', 'edit', 'delete'])

const formatDate = (date: string) => {
    return dayjs(date).format('MMMM D, YYYY')
}

const formatDateTime = (date: string | undefined) => {
    if (!date) return 'N/A'
    return dayjs(date).format('MMM D, YYYY h:mm A')
}

const formatHours = (minutes: number) => {
    const hours = minutes / 60
    return `${hours.toFixed(1)} hours`
}

const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}

const statusVariant = (status: string) => {
    const variants: Record<string, string> = {
        draft: 'secondary',
        ready: 'info',
        final: 'success',
        archived: 'dark'
    }
    return variants[status] || 'secondary'
}

const skillSignalVariant = (status: string) => {
    const variants: Record<string, string> = {
        suggested: 'warning',
        accepted: 'success',
        rejected: 'danger'
    }
    return variants[status] || 'secondary'
}

const bulletKindVariant = (kind: string) => {
    const variants: Record<string, string> = {
        note: 'secondary',
        status: 'info',
        resume: 'success'
    }
    return variants[kind] || 'secondary'
}
</script>
