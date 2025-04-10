<script setup>
import { computed } from "vue";
import { Modal } from "bootstrap";
import { ref, onMounted } from "vue";
import DeleteObjectModal from "@/components/objects/DeleteObjectModal.vue";
import { useAttachmentsStore } from "@/stores";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import {
  faFile,
  faFilePdf,
  faFileZipper,
  faFileLines,
  faFileImage,
  faFileCode,
  faFileWord,
  faFileExcel,
  faFileVideo,
  faFileCsv,
  faFileCircleExclamation,
  faFileAudio,
  faTrash,
  faDownload,
} from "@fortawesome/free-solid-svg-icons";

const props = defineProps(["attachment"]);
const attachment = ref(props.attachment);

const icons = {
  pdf: faFilePdf,
  zip: faFileZipper,
  txt: faFileLines,
  jpg: faFileImage,
  jpeg: faFileImage,
  png: faFileImage,
  gif: faFileImage,
  svg: faFileImage,
  mp4: faFileVideo,
  mp3: faFileAudio,
  doc: faFileWord,
  docx: faFileWord,
  xls: faFileExcel,
  xlsx: faFileExcel,
  csv: faFileCsv,
  js: faFileCode,
  py: faFileCode,
  c: faFileCode,
  cpp: faFileCode,
  h: faFileCode,
  hpp: faFileCode,
  html: faFileCode,
  css: faFileCode,
  json: faFileCode,
  xml: faFileCode,
  default: faFile,
};

const emit = defineEmits(["object-deleted", "attachment-deleted"]);

const attachmentsStore = useAttachmentsStore();

const deleteObjectModal = ref(null);

onMounted(() => {
  deleteObjectModal.value = new Modal(
    document.getElementById(`deleteObjectModal_${props.attachment.id}`),
  );
});

function openDeleteObjectModal() {
  deleteObjectModal.value.show();
}

function handleObjectDeleted() {
  emit("object-deleted", props.attachment.id);
  emit("attachment-deleted", props.attachment.id);
}

const filename = computed(
  () =>
    attachment.value.attributes.find(
      (attr) => attr.object_relation === "filename",
    )?.value || "attachment",
);

const isMalware = computed(() => {
  return (
    attachment.value.attributes.find(
      (attr) => attr.object_relation === "malware",
    )?.value || false
  );
});

const fileIcon = computed(() => {
  if (isMalware.value) {
    return faFileCircleExclamation;
  }

  const parts = filename.value.split(".");
  const extension = parts[parts.length - 1].toLowerCase();
  return icons[extension] || icons.default;
});

const size = computed(() => {
  const sizeAttr = attachment.value.attributes.find(
    (attr) => attr.object_relation === "size-in-bytes",
  );
  return sizeAttr ? `${(parseInt(sizeAttr.value) / 1024).toFixed(2)} KB` : "?";
});

async function downloadAttachment() {
  try {
    const response = await attachmentsStore.downloadAttachment(
      attachment.value.id,
    );

    if (!response.ok) {
      throw new Error("Failed to download file");
    }

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);

    const a = document.createElement("a");
    a.href = url;
    a.download = filename.value;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  } catch (error) {
    console.error("Download failed:", error);
  }
}
</script>

<style scoped>
.details {
  display: flex;
  flex-direction: column;
}

.name {
  font-weight: bold;
  text-overflow: ellipsis;
  overflow: hidden;
  white-space: nowrap;
}

.size {
  font-size: 0.8rem;
  color: #666;
}
</style>

<template>
  <div class="col-12 col-md-6 col-lg-2 col-xl-2">
    <div class="card m-2 file-card">
      <div class="card-body">
        <RouterLink :to="`/objects/${attachment.id}`">
          <div
            class="icon"
            data-toggle="tooltip"
            data-placement="bottom"
            :title="filename"
          >
            <FontAwesomeIcon
              :icon="fileIcon"
              class="fa-2xl"
              :class="{ 'text-danger': isMalware }"
            />
          </div>
          <div class="details small">
            <div class="name">{{ filename }}</div>
            <div class="size">{{ size }}</div>
          </div>
        </RouterLink>
      </div>
      <div class="card-footer">
        <div class="text-end">
          <div class="btn-group" role="group" aria-label="Attachment actions">
            <button
              type="button"
              class="btn btn-outline-primary"
              @click="downloadAttachment"
            >
              <FontAwesomeIcon :icon="faDownload" />
            </button>
            <button
              type="button"
              class="btn btn-danger"
              @click="openDeleteObjectModal"
            >
              <FontAwesomeIcon :icon="faTrash" />
            </button>
          </div>
          <DeleteObjectModal
            :key="attachment.id"
            :id="`deleteObjectModal_${attachment.id}`"
            @object-deleted="handleObjectDeleted"
            :modal="deleteObjectModal"
            :object_id="attachment.id"
          />
        </div>
      </div>
    </div>
  </div>
</template>
