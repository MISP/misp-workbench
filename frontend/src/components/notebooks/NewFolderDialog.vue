<script setup>
import { ref, watch } from "vue";

const props = defineProps({
  modalId: { type: String, default: "newFolderModal" },
  visibility: { type: String, required: true }, // "personal" | "global"
  parentId: { type: Number, default: null },
});

const emit = defineEmits(["create"]);

const name = ref("");
const error = ref(null);

watch(
  () => props.modalId,
  () => {
    name.value = "";
    error.value = null;
  },
);

function submit() {
  const trimmed = name.value.trim();
  if (!trimmed) {
    error.value = "Name is required";
    return;
  }
  emit("create", {
    name: trimmed,
    visibility: props.visibility,
    parent_id: props.parentId,
  });
}
</script>

<template>
  <div
    class="modal fade"
    :id="modalId"
    tabindex="-1"
    :aria-labelledby="`${modalId}Label`"
    aria-hidden="true"
  >
    <div class="modal-dialog">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title" :id="`${modalId}Label`">
            New folder
            <span
              class="badge ms-2"
              :class="visibility === 'global' ? 'bg-info' : 'bg-secondary'"
              >{{ visibility }}</span
            >
          </h5>
          <button
            type="button"
            class="btn-close"
            data-bs-dismiss="modal"
            aria-label="Close"
          ></button>
        </div>
        <div class="modal-body">
          <div class="mb-3">
            <label class="form-label small" for="nf-name">Name</label>
            <input
              id="nf-name"
              class="form-control form-control-sm"
              v-model="name"
              @keyup.enter="submit"
              autofocus
            />
          </div>
          <div v-if="error" class="alert alert-warning small mb-0">
            {{ error }}
          </div>
        </div>
        <div class="modal-footer">
          <button
            type="button"
            class="btn btn-outline-secondary btn-sm"
            data-bs-dismiss="modal"
          >
            Cancel
          </button>
          <button
            type="button"
            class="btn btn-primary btn-sm"
            data-bs-dismiss="modal"
            @click="submit"
          >
            Create
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
