<script setup>
import { ref } from "vue";

const props = defineProps({
  modalId: { type: String, default: "newNotebookModal" },
  visibility: { type: String, required: true }, // "personal" | "global"
  folderId: { type: Number, default: null },
});

const emit = defineEmits(["create"]);

const name = ref("");
const description = ref("");
const error = ref(null);

const STARTER_SOURCE = `# %% [id=__GENERATE__] code
# Welcome to your new notebook.
# Run cells with the toolbar above; outputs render inline.
mwlab
`;

function submit() {
  const trimmed = name.value.trim();
  if (!trimmed) {
    error.value = "Name is required";
    return;
  }
  // Cell ids are regenerated server-side on first save, but giving the
  // first cell a stable id keeps the editor behaviour predictable.
  const cellId = crypto.randomUUID
    ? crypto.randomUUID()
    : Math.random().toString(36).slice(2);
  const source = STARTER_SOURCE.replace("__GENERATE__", cellId);
  emit("create", {
    name: trimmed,
    description: description.value || null,
    visibility: props.visibility,
    folder_id: props.folderId,
    source,
  });
  name.value = "";
  description.value = "";
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
            New notebook
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
            <label class="form-label small" for="nn-name">Name</label>
            <input
              id="nn-name"
              class="form-control form-control-sm"
              v-model="name"
              @keyup.enter="submit"
              autofocus
            />
          </div>
          <div class="mb-3">
            <label class="form-label small" for="nn-desc">Description</label>
            <textarea
              id="nn-desc"
              class="form-control form-control-sm"
              rows="2"
              v-model="description"
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
