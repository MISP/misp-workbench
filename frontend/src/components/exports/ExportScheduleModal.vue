<script setup>
import { ref } from "vue";
import { useExportsStore, useToastsStore } from "@/stores";
import ExportScheduleFields from "@/components/exports/ExportScheduleFields.vue";

const props = defineProps({
  exportItem: { type: Object, required: true },
});

const emit = defineEmits(["saved", "close"]);

const exportsStore = useExportsStore();
const toastsStore = useToastsStore();

const scheduleModel = ref({
  schedule: props.exportItem.schedule || null,
  schedule_enabled: props.exportItem.schedule_enabled || false,
});

const apiError = ref(null);
const saving = ref(false);

async function save() {
  apiError.value = null;
  saving.value = true;
  try {
    await exportsStore.updateSchedule(props.exportItem.id, {
      schedule: scheduleModel.value.schedule,
      schedule_enabled: scheduleModel.value.schedule_enabled,
    });
    toastsStore.push(
      `Schedule updated for "${props.exportItem.name}".`,
      "success",
    );
    emit("saved");
  } catch (err) {
    apiError.value = err?.message || String(err);
  } finally {
    saving.value = false;
  }
}
</script>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: flex-start;
  justify-content: center;
  overflow-y: auto;
  padding: 2rem 1rem;
  z-index: 1050;
}
.modal-card {
  width: 620px;
  max-width: calc(100% - 2rem);
}
</style>

<template>
  <div class="modal-backdrop" @click.self="emit('close')">
    <div class="modal-card">
      <div class="card">
        <div
          class="card-header d-flex justify-content-between align-items-center"
        >
          <strong>Schedule — {{ exportItem.name }}</strong>
          <button type="button" class="btn-close" @click="emit('close')" />
        </div>
        <div class="card-body">
          <ExportScheduleFields v-model="scheduleModel" />
          <div v-if="apiError" class="alert alert-danger mt-3 mb-0">
            {{ apiError }}
          </div>
        </div>
        <div class="card-footer d-flex justify-content-end gap-2">
          <button class="btn btn-outline-secondary" @click="emit('close')">
            Cancel
          </button>
          <button class="btn btn-primary" :disabled="saving" @click="save">
            {{ saving ? "Saving…" : "Save schedule" }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
