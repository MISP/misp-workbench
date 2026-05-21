<script setup>
import { ref, computed } from "vue";
import { useFeedsStore } from "@/stores";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import {
  faSpinner,
  faCloudArrowUp,
  faFile,
  faXmark,
} from "@fortawesome/free-solid-svg-icons";

const props = defineProps({
  sourceFormat: {
    type: String,
    required: true,
  },
  filename: {
    type: String,
    default: "",
  },
  size: {
    type: Number,
    default: 0,
  },
  storageKey: {
    type: String,
    default: "",
  },
});

const emit = defineEmits(["uploaded", "cleared"]);

const feedsStore = useFeedsStore();

const dragOver = ref(false);
const uploading = ref(false);
const uploadError = ref(null);
const fileInputRef = ref(null);

const ACCEPT_BY_FORMAT = {
  csv: ".csv,.txt,text/csv,text/plain",
  json: ".json,.ndjson,application/json,text/plain",
  freetext: ".txt,.csv,text/plain,text/csv",
  misp: ".zip,.tar,.tar.gz,.tgz,application/zip,application/x-tar,application/gzip",
};

const acceptAttr = computed(() => ACCEPT_BY_FORMAT[props.sourceFormat] ?? "");

const hintText = computed(() => {
  switch (props.sourceFormat) {
    case "misp":
      return "Drop a MISP feed archive (.zip or .tar.gz). Must contain manifest.json.";
    case "csv":
      return "Drop a CSV file.";
    case "json":
      return "Drop a JSON or NDJSON file.";
    case "freetext":
      return "Drop a plain-text file (one indicator per line).";
    default:
      return "Drop a file to upload.";
  }
});

const formattedSize = computed(() => {
  if (!props.size) return "";
  const units = ["B", "KB", "MB", "GB"];
  let n = props.size;
  let i = 0;
  while (n >= 1024 && i < units.length - 1) {
    n /= 1024;
    i += 1;
  }
  return `${n.toFixed(n >= 10 || i === 0 ? 0 : 1)} ${units[i]}`;
});

function openPicker() {
  fileInputRef.value?.click();
}

function onFileSelected(event) {
  const file = event.target.files?.[0];
  if (file) uploadFile(file);
  event.target.value = "";
}

function onDrop(event) {
  event.preventDefault();
  dragOver.value = false;
  const file = event.dataTransfer?.files?.[0];
  if (file) uploadFile(file);
}

function onDragOver(event) {
  event.preventDefault();
  dragOver.value = true;
}

function onDragLeave() {
  dragOver.value = false;
}

async function uploadFile(file) {
  uploadError.value = null;
  uploading.value = true;
  try {
    const response = await feedsStore.uploadFile(file, props.sourceFormat);
    if (!response || !response.key) {
      uploadError.value = "Upload failed: no key returned";
      return;
    }
    emit("uploaded", {
      key: response.key,
      filename: response.filename,
      size: response.size,
    });
  } catch (error) {
    uploadError.value = error?.message || String(error);
  } finally {
    uploading.value = false;
  }
}

function clearFile() {
  uploadError.value = null;
  emit("cleared");
}
</script>

<template>
  <div class="feed-file-upload">
    <input
      ref="fileInputRef"
      type="file"
      class="d-none"
      :accept="acceptAttr"
      @change="onFileSelected"
    />

    <div
      v-if="!storageKey"
      class="dropzone p-4 border rounded text-center"
      :class="{ 'dropzone--active': dragOver, 'dropzone--busy': uploading }"
      @click="openPicker"
      @drop="onDrop"
      @dragover="onDragOver"
      @dragleave="onDragLeave"
    >
      <div v-if="uploading">
        <FontAwesomeIcon :icon="faSpinner" spin class="me-2" />
        Uploading…
      </div>
      <div v-else>
        <FontAwesomeIcon
          :icon="faCloudArrowUp"
          size="2x"
          class="mb-2 text-secondary"
        />
        <div class="fw-semibold">Click to select or drop a file here</div>
        <div class="text-muted small mt-1">{{ hintText }}</div>
      </div>
    </div>

    <div
      v-else
      class="d-flex align-items-center justify-content-between border rounded p-3"
    >
      <div class="d-flex align-items-center">
        <FontAwesomeIcon :icon="faFile" class="me-2 text-secondary" />
        <div>
          <div class="fw-semibold">{{ filename || storageKey }}</div>
          <div v-if="formattedSize" class="text-muted small">
            {{ formattedSize }}
          </div>
        </div>
      </div>
      <div class="d-flex gap-2">
        <button
          type="button"
          class="btn btn-outline-secondary btn-sm"
          :disabled="uploading"
          @click="openPicker"
        >
          <FontAwesomeIcon
            v-if="uploading"
            :icon="faSpinner"
            spin
            class="me-1"
          />
          Replace
        </button>
        <button
          type="button"
          class="btn btn-outline-danger btn-sm"
          :disabled="uploading"
          @click="clearFile"
        >
          <FontAwesomeIcon :icon="faXmark" />
        </button>
      </div>
    </div>

    <div v-if="uploadError" class="alert alert-danger mt-2 mb-0">
      {{ uploadError }}
    </div>
  </div>
</template>

<style scoped>
.dropzone {
  background: var(--bs-body-bg);
  cursor: pointer;
  border-style: dashed !important;
  transition: background-color 0.15s ease;
}
.dropzone:hover,
.dropzone--active {
  background: var(--bs-secondary-bg, #f1f3f5);
}
.dropzone--busy {
  cursor: progress;
  opacity: 0.7;
}
</style>
