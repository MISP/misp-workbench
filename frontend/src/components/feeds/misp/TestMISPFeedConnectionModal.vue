<script setup>
defineProps({
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

<template>
  <div class="test-modal-backdrop">
    <div class="test-modal">
      <div class="card">
        <div
          class="card-header d-flex justify-content-between align-items-center"
        >
          <div>
            <strong>Connection Test</strong>
          </div>
        </div>
        <div class="card-body">
          <div v-if="testResult.success" class="alert alert-success">
            {{ testResult.message }}
          </div>
          <div v-else class="alert alert-danger">
            {{ testResult.message }}
          </div>
          <div v-if="testResult.total_events">
            <p class="mb-0">
              <strong>Total feed events:</strong> {{ testResult.total_events }}
            </p>
          </div>
          <div v-if="testResult.total_filtered_events">
            <p class="mb-0">
              <strong>Total events to fetch:</strong>
              {{ testResult.total_filtered_events }}
            </p>
          </div>
        </div>
        <div class="card-footer text-end">
          <button class="btn btn-secondary" @click="closeModal">Close</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.test-modal-backdrop {
  position: fixed;
  left: 0;
  top: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
}

.test-modal .card {
  width: 520px;
  max-width: calc(100% - 2rem);
}
</style>
