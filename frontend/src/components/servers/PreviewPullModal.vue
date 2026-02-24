<script setup>
defineProps({
  result: { type: Object, default: null },
  error: { type: String, default: null },
});

const emit = defineEmits(["close"]);
</script>

<template>
  <div class="preview-modal-backdrop" @click.self="emit('close')">
    <div class="preview-modal">
      <div class="card">
        <div
          class="card-header d-flex justify-content-between align-items-center"
        >
          <strong>Pull Preview</strong>
          <button type="button" class="btn-close" @click="emit('close')" />
        </div>
        <div class="card-body">
          <div v-if="error" class="alert alert-danger mb-0">
            {{ error }}
          </div>
          <template v-else-if="result">
            <div class="alert alert-success mb-3">
              {{ result.message }}
            </div>
            <div class="row text-center">
              <div class="col">
                <div class="fs-2 fw-bold">{{ result.total }}</div>
                <div class="text-muted small">
                  Total events on remote server
                </div>
              </div>
              <div class="col border-start">
                <div class="fs-2 fw-bold text-primary">
                  {{ result.total_filtered }}
                </div>
                <div class="text-muted small">Events matching pull rules</div>
              </div>
            </div>
          </template>
        </div>
        <div class="card-footer text-end">
          <button
            type="button"
            class="btn btn-secondary"
            @click="emit('close')"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.preview-modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1050;
}

.preview-modal {
  width: 480px;
  max-width: 95%;
}
</style>
