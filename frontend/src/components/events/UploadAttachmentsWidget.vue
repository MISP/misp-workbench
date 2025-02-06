<script setup>
import { ref } from "vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { storeToRefs } from "pinia";
import { useEventsStore } from "@/stores";
import { faPaperclip } from "@fortawesome/free-solid-svg-icons";

const props = defineProps(["event_id"]);
const emit = defineEmits(["object-added"]);

const eventsStore = useEventsStore();
const { status } = storeToRefs(eventsStore);

const files = ref([]);
const fileInput = ref(null);

const selectFile = () => {
  fileInput.value.click();
};

const handleFileSelect = (event) => {
  addFiles(event.target.files);
};

const dropFile = (event) => {
  addFiles(event.dataTransfer.files);
};

const addFiles = (fileList) => {
  for (const file of fileList) {
    if (!files.value.some((f) => f.name === file.name)) {
      files.value.push(file);
    }
  }
};

const removeFile = (index) => {
  files.value.splice(index, 1);
};

const formatSize = (size) => {
  return (size / 1024).toFixed(2) + " KB";
};

const uploadFiles = () => {
  if (files.value.length === 0) return;

  const formData = new FormData();
  files.value.forEach((file) => {
    formData.append("attachments", file);
  });

  eventsStore
    .upload_attachments(props.event_id, formData)
    .then((response) => {
      files.value = [];
      status.value = { uploading: false };
      response.forEach((object) => {
        emit("object-added", object);
      });
    })
    .catch((error) => {
      status.value = { uploading: false, error: error };
    })
    .finally(() => {
      status.value = { uploading: false };
    });
};
</script>

<style>
.drop-zone {
  cursor: pointer;
  padding: 30px;
  border-style: dashed !important;
}
</style>
<template>
  <div class="card">
    <div class="card-header">
      <FontAwesomeIcon :icon="faPaperclip" /> attachments
    </div>
    <div class="card-body">
      <div
        class="drop-zone border-3 dary m-2 border-light"
        @dragover.prevent="dragOver"
        @drop.prevent="dropFile"
        @click="selectFile"
      >
        <input
          type="file"
          multiple
          @change="handleFileSelect"
          ref="fileInput"
          hidden
        />
        <p class="text-center text-secondary">
          Drag & Drop files here or click to upload file attachments
        </p>
      </div>
      <ul class="list-group mt-3" v-if="files.length">
        <li
          class="list-group-item d-flex justify-content-between align-items-center"
          v-for="(file, index) in files"
          :key="index"
        >
          {{ file.name }} ({{ formatSize(file.size) }})
          <button class="btn btn-danger btn-sm" @click="removeFile(index)">
            Remove
          </button>
        </li>
      </ul>
      <div class="text-center mt-3">
        <button
          class="btn btn-primary"
          @click="uploadFiles"
          :disabled="files.length === 0 || status.uploading"
        >
          <span v-if="status.uploading">
            <span
              class="spinner-border spinner-border-sm"
              role="status"
              aria-hidden="true"
            >
            </span>
          </span>
          <span v-if="!status.uploading">Upload Files</span>
        </button>
      </div>
    </div>
  </div>
</template>
