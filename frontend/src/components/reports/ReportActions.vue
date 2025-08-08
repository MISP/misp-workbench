<script setup>
import { authHelper } from "@/helpers";
import { ref, computed, onMounted } from "vue";
import { Modal } from "bootstrap";
import { storeToRefs } from "pinia";
import { useAuthStore } from "@/stores";
import DeleteReportModal from "@/components/reports/DeleteReportModal.vue";
import CreateOrEditReportModal from "@/components/reports/CreateOrEditReportModal.vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faTrash, faPen } from "@fortawesome/free-solid-svg-icons";

const authStore = useAuthStore();
const { scopes } = storeToRefs(authStore);

const props = defineProps({
  report: Object,
  default_actions: {
    type: Object,
    default: () => ({}),
  },
});

const actions = computed(() => ({
  index:
    props.default_actions.index ??
    authHelper.hasScope(scopes.value, "reports:index"),
  view:
    props.default_actions.view ??
    authHelper.hasScope(scopes.value, "reports:view"),
  update:
    props.default_actions.update ??
    authHelper.hasScope(scopes.value, "reports:update"),
  delete:
    props.default_actions.delete ??
    authHelper.hasScope(scopes.value, "reports:delete"),
  tag:
    props.default_actions.tag ??
    authHelper.hasScope(scopes.value, "reports:tag"),
}));

const deleteReportModal = ref(null);
const createOrEditReportModal = ref(null);

onMounted(() => {
  deleteReportModal.value = new Modal(
    document.getElementById(`deleteReportModal_${props.report._id}`),
  );
  createOrEditReportModal.value = new Modal(
    document.getElementById(`createOrEditReportModal_${props.report._id}`),
  );
});

function openDeleteReportModal() {
  deleteReportModal.value.show();
}

function openCreateorEditReportModal() {
  createOrEditReportModal.value.show();
}

const emit = defineEmits(["report-updated", "report-deleted"]);

function handleReportDeleted(r) {
  emit("report-deleted", r);
}

function handleReportUpdated(r) {
  emit("report-updated", r);
}
</script>

<style scoped>
.btn-toolbar {
  flex-wrap: nowrap !important;
}
</style>

<template>
  <div class="btn-toolbar float-end" role="toolbar">
    <div
      :class="{ 'btn-group-vertical': $isMobile, 'btn-group me-2': !$isMobile }"
      role="group"
      aria-label="Event Report Actions"
    >
      <button
        v-if="actions.update"
        type="button"
        class="btn btn-outline-primary btn-sm"
        data-placement="top"
        data-toggle="tooltip"
        title="Delete report"
        @click="openCreateorEditReportModal"
      >
        <FontAwesomeIcon :icon="faPen" />
      </button>
    </div>
    <div class="btn-group me-2" role="group">
      <button
        v-if="actions.delete"
        type="button"
        class="btn btn-danger btn-sm"
        data-placement="top"
        data-toggle="tooltip"
        title="Delete report"
        @click="openDeleteReportModal"
      >
        <FontAwesomeIcon :icon="faTrash" />
      </button>
    </div>
  </div>
  <DeleteReportModal
    :key="report._id"
    :id="`deleteReportModal_${report._id}`"
    @report-deleted="handleReportDeleted"
    :modal="deleteReportModal"
    :report_uuid="report._id"
  />
  <CreateOrEditReportModal
    :key="report._id"
    :id="`createOrEditReportModal_${report._id}`"
    @report-updated="handleReportUpdated"
    :modal="createOrEditReportModal"
    :event_uuid="props.report._source.event_uuid"
    :existing_report="props.report"
  />
</template>
