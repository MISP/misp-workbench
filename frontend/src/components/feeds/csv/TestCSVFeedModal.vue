<script setup>
import { ref } from "vue";
import CsvPreview from "./CsvPreview.vue";

const showRaw = ref(false);

defineProps({
  config: {
    type: Object,
    required: true,
  },
  testResult: {
    type: Object,
    required: true,
  },
});

const emit = defineEmits(["closeModal"]);

function closeModal() {
  emit("closeModal");
}
</script>
<style scoped>
.test-modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1050;
}

.test-modal {
  width: 800px;
  max-width: 95%;
  max-height: 90vh;
  overflow-y: auto;
}
</style>
<template>
  <div class="test-modal-backdrop">
    <div class="test-modal">
      <div class="card">
        <!-- HEADER -->
        <div
          class="card-header d-flex justify-content-between align-items-center"
        >
          <strong>CSV Feed Test Result</strong>
          <button class="btn btn-sm btn-outline-secondary" @click="closeModal">
            ✕
          </button>
        </div>

        <div class="card-body">
          <div v-if="testResult.rows?.length" class="table-responsive">
            <div class="card mb-2">
              <div class="card-body">
                <CsvPreview
                  v-if="testResult.rows?.length"
                  :columns="config.settings.csvConfig.columns"
                  :rows="testResult.rows"
                  :preview="testResult.preview"
                />
              </div>
            </div>
          </div>
          <!-- EMPTY STATE -->
          <div v-else class="text-muted text-center py-4">No rows parsed.</div>

          <hr />

          <!-- RAW JSON -->
          <div>
            <button
              class="btn btn-sm btn-outline-secondary mb-2"
              @click="showRaw = !showRaw"
            >
              {{ showRaw ? "Hide" : "Show" }} Raw JSON Results
            </button>

            <div v-if="showRaw">
              <pre class="p-3 rounded small overflow-auto">
      {{ JSON.stringify(testResult, null, 2) }}
    </pre
              >
            </div>
          </div>
        </div>

        <div class="card-footer text-end">
          <button class="btn btn-secondary" @click="closeModal">Close</button>
        </div>
      </div>
    </div>
  </div>
</template>
