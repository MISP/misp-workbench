<script setup>
import { ref } from "vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { storeToRefs } from "pinia";
import { useAttachmentsStore } from "@/stores";
import { faCloudArrowUp, faPaperclip } from "@fortawesome/free-solid-svg-icons";
import AttachmentIcon from "@/components/attachments/AttachmentIcon.vue";
import Spinner from "@/components/misc/Spinner.vue";

const props = defineProps(["event_id"]);
const emit = defineEmits(["object-added", "object-deleted"]);

const attachmentsStore = useAttachmentsStore();
const { attachments, status } = storeToRefs(attachmentsStore);

attachmentsStore.getEventAttachments(props.event_id);

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
      file.is_malware = false;
      file.category = "Payload delivery";
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

  const attachments_meta = {};
  const formData = new FormData();
  files.value.forEach((file) => {
    formData.append("attachments", file);
    attachments_meta[file.name] = {
      is_malware: file.is_malware,
      category: file.category,
    };
  });
  formData.append("attachments_meta", JSON.stringify(attachments_meta));

  attachmentsStore
    .uploadAttachments(props.event_id, formData)
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

function handleAttachmentDeleted(attachment_id) {
  attachments.value = attachments.value.filter(
    (attachment) => attachment.id !== attachment_id,
  );
}

function handleObjectDeleted(object_id) {
  emit("object-deleted", object_id);
}
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
      <Spinner v-if="status.loading" />
      <div class="row row-cols-1 row-cols-md-2">
        <AttachmentIcon
          v-for="attachment in attachments"
          :key="attachment.id"
          :attachment="attachment"
          @object-deleted="handleObjectDeleted"
          @attachment-deleted="handleAttachmentDeleted"
        />
      </div>
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
          <FontAwesomeIcon :icon="faCloudArrowUp" class="fa-2xl" /> Drag & Drop
          files here or click to upload file attachments
        </p>
      </div>
      <div class="mt-3" v-for="(file, index) in files" :key="index">
        <div>
          <div class="input-group mb-3">
            <span
              class="input-group-text"
              id="basic-addon1"
              style="width: 50%"
              >{{ file.name }}</span
            >
            <span class="input-group-text" id="basic-addon1">{{
              formatSize(file.size)
            }}</span>
            <label class="input-group-text" for="file.is_malware"
              >malware</label
            >
            <div class="input-group-text">
              <input
                class="form-check-input mt-0"
                type="checkbox"
                v-model="file.is_malware"
                aria-label="Checkbox for following text input"
              />
            </div>
            <select
              class="form-select"
              aria-label="Default select example"
              v-model="file.category"
            >
              <option>Payload delivery</option>
              <option>Artifacts dropped</option>
              <option>Payload installation</option>
              <option>External analysis</option>
            </select>
            <button class="btn btn-danger btn-sm" @click="removeFile(index)">
              Remove
            </button>
          </div>
        </div>
      </div>
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
