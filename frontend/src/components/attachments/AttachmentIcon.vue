<script setup>
import { computed } from "vue";
import { Modal } from "bootstrap";
import { ref, onMounted } from "vue";
import DeleteObjectModal from "@/components/objects/DeleteObjectModal.vue";
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
    )?.value || "",
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
  return icons[extension];
});

const size = computed(() => {
  const sizeAttr = attachment.value.attributes.find(
    (attr) => attr.object_relation === "size-in-bytes",
  );
  return sizeAttr ? `${(parseInt(sizeAttr.value) / 1024).toFixed(2)} KB` : "?";
});
</script>

<style scoped>
.file-item {
  background: #f9f9f9;
  width: 140px;
}

.details {
  display: flex;
  flex-direction: column;
}

.name {
  font-weight: bold;
  text-overflow: ellipsis;
  overflow: hidden;
  white-space: nowrap;
  width: 100px;
}

.size {
  font-size: 0.8rem;
  color: #666;
}
</style>

<template>
  <div class="file-item card m-2">
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
        <div class="details">
          <div class="name small">{{ filename }}</div>
          <div class="size">{{ size }}</div>
        </div>
      </RouterLink>
    </div>
    <div class="card-footer">
      <div
        class="btn-group text-center"
        role="group"
        aria-label="Attachment actions"
      >
        <button type="button" class="btn btn-outline-primary">
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
</template>
