<template>
  <div>
    <b-form
      action="/"
      method="post"
      class="dropzone"
      id="myAwesomeDropzone"
      v-bind="getRootProps()"
    >
      <div class="fallback">
        <input name="file" v-bind="getInputProps()" @change="onChange" />
      </div>

      <div class="dz-message needsclick">
        <div class="avatar-lg mx-auto mb-3">
          <span class="avatar-title bg-info-subtle text-info rounded-circle">
            <Icon icon="lucide:cloud-upload" class="fs-24 ti ti-cloud-upload" />
          </span>
        </div>
        <h4 class="mb-2">Drop files here or click to upload.</h4>
        <p class="text-muted fst-italic mb-3">
          {{ accept || 'You can drag files here, or browse files via the button below.' }}
        </p>
        <button type="button" class="btn btn-sm shadow btn-primary">
          Browse Files
        </button>
      </div>
    </b-form>

    <div
      v-if="state.files.length > 0"
      class="dropzone-previews mt-3"
      id="uploadPreviewTemplate"
    >
      <div
        v-for="(file, index) in state.files"
        :key="file.name + index"
        class="card mb-1 shadow-none border border-dashed"
      >
        <div class="p-2">
          <BRow class="align-items-center">
            <BCol class="col-auto">
              <Icon 
                :icon="getFileIcon(file.name)" 
                class="fs-32" 
                :class="uploading ? 'text-muted' : 'text-primary'"
              />
            </BCol>

            <BCol class="ps-0">
              <a class="fw-semibold">{{ file.name }}</a>
              <p class="mb-0">{{ getSize(file) }}</p>
              <p v-if="uploading" class="mb-0 text-muted small">Uploading...</p>
            </BCol>

            <BCol class="col-auto">
              <button
                type="button"
                @click="handleClickDeleteFile(index)"
                class="btn btn-link btn-lg text-danger"
                :disabled="uploading"
              >
                <Icon icon="tabler:x" />
              </button>
            </BCol>
          </BRow>
        </div>
      </div>
    </div>

    <div v-if="state.files.length > 0 && !uploading" class="mt-3 text-end">
      <BButton variant="primary" @click="uploadFiles" :disabled="uploading">
        <Icon icon="tabler:upload" class="me-1" />
        Upload {{ state.files.length }} file{{ state.files.length > 1 ? 's' : '' }}
      </BButton>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useDropzone } from "vue3-dropzone";
import { reactive, onBeforeUnmount, ref } from "vue";
import { BCol, BRow, BButton } from "bootstrap-vue-next";
import { Icon } from "@iconify/vue";

// Props
const props = defineProps<{
  accept?: string
  maxFiles?: number
  maxFileSize?: number
}>()

// Emit
const emit = defineEmits<{
  'files-uploaded': [files: File[]]
}>()

// extend File with previewUrl
type FileWithPreview = File & { previewUrl: string };

// reactive state
const state = reactive<{ files: FileWithPreview[] }>({
  files: [],
});

const uploading = ref(false)

// dropzone setup
function onDrop(acceptFiles: File[]) {
  const newFiles = acceptFiles
    .slice(0, props.maxFiles || 10)
    .filter((file) => {
      if (props.maxFileSize && file.size > props.maxFileSize) {
        alert(`File ${file.name} is too large. Maximum size is ${(props.maxFileSize / 1024 / 1024).toFixed(2)} MB`)
        return false
      }
      return true
    })
    .map((file) => {
      const f = file as FileWithPreview;
      f.previewUrl = URL.createObjectURL(file);
      return f;
    });
  state.files.push(...newFiles); 
}

const { getRootProps, getInputProps } = useDropzone({
  onDrop,
  multiple: true,
  accept: props.accept,
});

// delete file + cleanup
function handleClickDeleteFile(index: number) {
  const file = state.files[index];
  if (file?.previewUrl) {
    URL.revokeObjectURL(file.previewUrl);
  }
  state.files.splice(index, 1);
}

// upload files
async function uploadFiles() {
  if (state.files.length === 0) return
  
  uploading.value = true
  try {
    // Emit the files to parent component for upload
    emit('files-uploaded', state.files as File[])
    
    // Clear files after emitting
    state.files.forEach((file:any) => {
      if (file.previewUrl) URL.revokeObjectURL(file.previewUrl);
    });
    state.files = []
  } catch (error) {
    console.error('Upload error:', error)
  } finally {
    uploading.value = false
  }
}

// cleanup all previews on unmount
onBeforeUnmount(() => {
  state.files.forEach((file:any) => {
    if (file.previewUrl) URL.revokeObjectURL(file.previewUrl);
  });
});

// file size helper
function getSize(file: File | undefined) {
  if (!file) return "";
  if (file.size / (1024 * 1024) >= 1) {
    return (file.size / (1024 * 1024)).toFixed(2) + " MB";
  }
  return (file.size / 1024).toFixed(2) + " KB";
}

// file icon helper
function getFileIcon(filename: string) {
  const ext = filename.split('.').pop()?.toLowerCase()
  const iconMap: Record<string, string> = {
    pdf: 'tabler:file-type-pdf',
    doc: 'tabler:file-type-doc',
    docx: 'tabler:file-type-docx',
    txt: 'tabler:file-type-txt',
    jpg: 'tabler:photo',
    jpeg: 'tabler:photo',
    png: 'tabler:photo',
    gif: 'tabler:photo',
    zip: 'tabler:file-zip',
    default: 'tabler:file'
  }
  return iconMap[ext || ''] || iconMap.default
}

function onChange() {
  if (state.files[0]) {
    getSize(state.files[0]);
  }
}
</script>
