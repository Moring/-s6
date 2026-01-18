<template>
    <div style="padding: 20px; background: white; min-height: 100vh;">
        <h1 style="color: green;">✓ Worklog Page is Rendering!</h1>
        
        <div style="margin: 20px 0; padding: 15px; border: 2px solid #007bff; border-radius: 5px;">
            <h2>Debug Information</h2>
            <p><strong>Logged in:</strong> {{ isLoggedIn ? 'Yes' : 'No' }}</p>
            <p><strong>User:</strong> {{ currentUser?.username || 'Not available' }}</p>
            <p><strong>API Base URL:</strong> {{ apiBaseUrl }}</p>
        </div>

        <div style="margin: 20px 0;">
            <button 
                @click="testConnection" 
                style="padding: 10px 20px; background: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer;"
            >
                Test API Connection
            </button>
        </div>

        <div v-if="testResult" style="margin: 20px 0; padding: 15px; background: #f8f9fa; border-radius: 5px;">
            <h3>Test Result:</h3>
            <pre style="white-space: pre-wrap; word-wrap: break-word;">{{ JSON.stringify(testResult, null, 2) }}</pre>
        </div>

        <div style="margin: 20px 0;">
            <button 
                @click="fetchData" 
                style="padding: 10px 20px; background: #28a745; color: white; border: none; border-radius: 5px; cursor: pointer;"
            >
                Fetch Worklogs
            </button>
        </div>

        <div v-if="worklogData" style="margin: 20px 0; padding: 15px; background: #f8f9fa; border-radius: 5px;">
            <h3>Worklog Data:</h3>
            <pre style="white-space: pre-wrap; word-wrap: break-word;">{{ JSON.stringify(worklogData, null, 2) }}</pre>
        </div>

        <div v-if="error" style="margin: 20px 0; padding: 15px; background: #f8d7da; border: 1px solid #f5c6cb; border-radius: 5px; color: #721c24;">
            <h3>Error:</h3>
            <pre style="white-space: pre-wrap; word-wrap: break-word;">{{ error }}</pre>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import authService from '@/services/auth.service'
import apiClient from '@/services/api'
import { worklogService } from '@/services/worklog.service'

const testResult = ref<any>(null)
const worklogData = ref<any>(null)
const error = ref<string | null>(null)

const isLoggedIn = computed(() => authService.isAuthenticated())
const currentUser = computed(() => authService.getCurrentUser())
const apiBaseUrl = computed(() => import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000')

const testConnection = async () => {
    testResult.value = null
    error.value = null
    try {
        const response = await apiClient.get('/api/healthz/')
        testResult.value = {
            status: 'Success',
            statusCode: response.status,
            data: response.data
        }
    } catch (err: any) {
        error.value = `API Connection Failed: ${err.message}\n${JSON.stringify(err.response?.data || {}, null, 2)}`
    }
}

const fetchData = async () => {
    worklogData.value = null
    error.value = null
    try {
        const data = await worklogService.list({ page: 1, limit: 10 })
        worklogData.value = {
            count: data.count,
            resultsCount: data.results?.length || 0,
            results: data.results
        }
    } catch (err: any) {
        error.value = `Failed to fetch worklogs: ${err.message}\n${err.toString()}`
    }
}
</script>
