<template>
    <MainLayout>
        <BContainer fluid>
            <h1>Worklog Debug</h1>
            
            <div class="mb-3">
                <h3>API Configuration</h3>
                <pre>{{ apiConfig }}</pre>
            </div>

            <div class="mb-3">
                <h3>Auth Status</h3>
                <pre>{{ authStatus }}</pre>
            </div>

            <div class="mb-3">
                <h3>Test Results</h3>
                <BButton @click="testAPI" class="mb-2">Test API Connection</BButton>
                <pre v-if="testResults">{{ testResults }}</pre>
            </div>

            <div class="mb-3">
                <h3>Fetch Worklogs</h3>
                <BButton @click="fetchWorklogs" class="mb-2">Fetch Worklogs</BButton>
                <pre v-if="worklogResults">{{ JSON.stringify(worklogResults, null, 2) }}</pre>
            </div>
        </BContainer>
    </MainLayout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import MainLayout from '@/layouts/MainLayout.vue'
import apiClient from '@/services/api'
import { worklogService } from '@/services/worklog.service'

const testResults = ref<any>(null)
const worklogResults = ref<any>(null)

const apiConfig = computed(() => ({
    baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
    hasToken: !!localStorage.getItem('access_token'),
    hasUser: !!localStorage.getItem('user')
}))

const authStatus = computed(() => ({
    token: localStorage.getItem('access_token')?.substring(0, 20) + '...',
    user: localStorage.getItem('user')
}))

const testAPI = async () => {
    try {
        const response = await apiClient.get('/api/healthz/')
        testResults.value = {
            success: true,
            status: response.status,
            data: response.data
        }
    } catch (error: any) {
        testResults.value = {
            success: false,
            error: error.message,
            response: error.response?.data,
            status: error.response?.status
        }
    }
}

const fetchWorklogs = async () => {
    try {
        const data = await worklogService.list({ page: 1, limit: 10 })
        worklogResults.value = {
            success: true,
            count: data.count,
            results: data.results?.length || 0,
            data: data
        }
    } catch (error: any) {
        worklogResults.value = {
            success: false,
            error: error.message,
            details: error.toString()
        }
    }
}

onMounted(() => {
    console.log('Debug page mounted')
    console.log('API Config:', apiConfig.value)
    console.log('Auth Status:', authStatus.value)
})
</script>
