<script setup>
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

<template>
  <div class="test-modal-backdrop">
    <div class="test-modal">
      <div class="card">
        <div
          class="card-header d-flex justify-content-between align-items-center"
        >
          <div>
            <strong>CSV Feed Test</strong>
          </div>
        </div>
        <div class="card-body">
          {{ config }}
        </div>
        <div class="card-footer text-end">
          <button class="btn btn-secondary" @click="closeModal">Close</button>
        </div>
      </div>
    </div>
  </div>
</template>
