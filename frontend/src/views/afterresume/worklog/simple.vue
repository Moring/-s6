<template>
    <div class="container-fluid p-4">
        <h1>Worklog - Simple Test</h1>
        <p>If you can see this, the routing works.</p>
        
        <div class="mb-3">
            <h3>Test 1: Basic Data</h3>
            <button class="btn btn-primary" @click="test1">Test API</button>
            <pre v-if="test1Result">{{ JSON.stringify(test1Result, null, 2) }}</pre>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { worklogService } from '@/services/worklog.service'

const test1Result = ref<any>(null)

const test1 = async () => {
    try {
        test1Result.value = { status: 'Loading...' }
        const data = await worklogService.list({ page: 1, limit: 5 })
        test1Result.value = {
            success: true,
            count: data.count,
            results: data.results?.length || 0
        }
    } catch (error: any) {
        test1Result.value = {
            success: false,
            error: error.message
        }
    }
}
</script>
