<script setup>
import { Modal } from "bootstrap";
import { ref } from "vue";

defineProps({
  periodDays: { type: Number, default: 365 },
  affectedCount: { type: Number, default: 0 },
});

const emit = defineEmits(["confirmed"]);

const modalEl = ref(null);

defineExpose({ $el: modalEl });

function onConfirm() {
  emit("confirmed");
  Modal.getInstance(modalEl.value)?.hide();
}
</script>

<template>
  <div
    ref="modalEl"
    class="modal fade"
    tabindex="-1"
    aria-labelledby="retentionConfirmModalLabel"
    aria-hidden="true"
  >
    <div class="modal-dialog">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title" id="retentionConfirmModalLabel">
            Confirm Retention Settings
          </h5>
          <button
            type="button"
            class="btn-close"
            data-bs-dismiss="modal"
            aria-label="Close"
          ></button>
        </div>
        <div class="modal-body">
          Setting the retention period to
          <strong>{{ periodDays }} days</strong> will make
          <strong>{{ affectedCount }} event(s)</strong> eligible for deletion.
          Events tagged with any of the configured exempt tags are excluded.
        </div>
        <div class="modal-footer">
          <button
            type="button"
            class="btn btn-secondary"
            data-bs-dismiss="modal"
          >
            Discard
          </button>
          <button type="button" class="btn btn-danger" @click="onConfirm">
            Confirm
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
