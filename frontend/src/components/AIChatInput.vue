<template>
  <div class="ai-chat-input mb-4">
    <div class="chat-container">
      <form @submit.prevent="handleSubmit" class="chat-form">
        <div class="input-container">
          <textarea
            ref="textareaRef"
            v-model="inputText"
            class="chat-textarea"
            placeholder="Ask anything..."
            rows="1"
            @keydown="handleKeydown"
            @input="adjustHeight"
          ></textarea>
          <div class="toolbar">
            <div class="toolbar-left">
              <span class="model-indicator">
                <strong>DM</strong> AI Assistant
              </span>
            </div>
            <div class="toolbar-right">
              <button
                type="submit"
                class="btn-send"
                :disabled="!inputText.trim() || sending"
                title="Send (Enter)"
              >
                <Icon v-if="sending" icon="tabler:loader-2" class="spinning" />
                <Icon v-else icon="tabler:send" />
              </button>
            </div>
          </div>
        </div>
      </form>
    </div>

    <!-- Response Display -->
    <div v-if="response" class="response-container mt-3">
      <div class="response-content bg-light p-3 rounded">
        <div class="d-flex justify-content-between align-items-start mb-2">
          <strong class="text-primary">
            <Icon icon="tabler:robot" class="me-1" />
            AI Response
          </strong>
          <button 
            type="button" 
            class="btn btn-sm btn-link text-muted p-0"
            @click="response = ''"
            title="Close"
          >
            <Icon icon="tabler:x" />
          </button>
        </div>
        <div v-html="formattedResponse" class="response-text"></div>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="sending" class="loading-container mt-3 text-center">
      <div class="spinner-border spinner-border-sm text-primary" role="status">
        <span class="visually-hidden">Loading...</span>
      </div>
      <span class="ms-2 text-muted">Thinking...</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick } from 'vue'
import { Icon } from '@iconify/vue'

// Props
const props = defineProps<{
  context?: string
  placeholder?: string
}>()

const inputText = ref('')
const response = ref('')
const sending = ref(false)
const textareaRef = ref<HTMLTextAreaElement | null>(null)

const adjustHeight = () => {
  if (textareaRef.value) {
    textareaRef.value.style.height = 'auto'
    textareaRef.value.style.height = Math.min(textareaRef.value.scrollHeight, 120) + 'px'
  }
}

const handleKeydown = (e: KeyboardEvent) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSubmit()
  }
}

const handleSubmit = async () => {
  if (!inputText.value.trim() || sending.value) return

  const query = inputText.value
  inputText.value = ''
  sending.value = true
  response.value = ''

  // Reset textarea height
  await nextTick()
  if (textareaRef.value) {
    textareaRef.value.style.height = 'auto'
  }

  try {
    // TODO: Implement actual AI API call
    // For now, simulate a response
    await new Promise((resolve) => setTimeout(resolve, 1500))
    response.value = `I received your query: "${query}". This is a placeholder response. The AI integration will be completed in the backend implementation phase.`
  } catch (error) {
    console.error('Failed to get AI response:', error)
    response.value = 'Sorry, I encountered an error. Please try again.'
  } finally {
    sending.value = false
  }
}

const formattedResponse = computed(() => {
  // Simple markdown-like formatting
  return response.value
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>')
})
</script>

<script lang="ts">
import { computed } from 'vue'
export default {
  name: 'AIChatInput'
}
</script>

<style scoped>
.ai-chat-input {
  width: 100%;
}

.chat-container {
  width: 100%;
  background: white;
  border: 1px solid #dee2e6;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.chat-form {
  width: 100%;
}

.input-container {
  position: relative;
  padding: 12px;
}

.chat-textarea {
  width: 100%;
  border: none;
  outline: none;
  resize: none;
  font-size: 14px;
  line-height: 1.5;
  padding: 8px 12px;
  border-radius: 4px;
  background: #f8f9fa;
  min-height: 42px;
  max-height: 120px;
  overflow-y: auto;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
}

.chat-textarea:focus {
  background: white;
  box-shadow: 0 0 0 2px rgba(13, 110, 253, 0.25);
}

.chat-textarea::placeholder {
  color: #6c757d;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid #e9ecef;
}

.toolbar-left {
  flex: 1;
}

.model-indicator {
  font-size: 12px;
  color: #6c757d;
}

.model-indicator strong {
  color: #0d6efd;
  font-weight: 700;
}

.toolbar-right {
  display: flex;
  gap: 8px;
  align-items: center;
}

.btn-send {
  background: #0d6efd;
  color: white;
  border: none;
  border-radius: 6px;
  padding: 8px 16px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
}

.btn-send:hover:not(:disabled) {
  background: #0b5ed7;
  transform: translateY(-1px);
}

.btn-send:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.response-container {
  animation: slideIn 0.3s ease-out;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.response-content {
  border: 1px solid #dee2e6;
}

.response-text {
  font-size: 14px;
  line-height: 1.6;
  color: #212529;
  white-space: pre-wrap;
}

.loading-container {
  animation: fadeIn 0.3s ease-in;
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}
</style>
