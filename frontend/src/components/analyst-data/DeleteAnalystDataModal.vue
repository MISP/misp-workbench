<script setup>
import { computed } from "vue";
import { storeToRefs } from "pinia";
import { useAnalystDataStore } from "@/stores";

const props = defineProps({
  id: { type: String, required: true },
  modal: Object,
  node: { type: Object, default: null },
});

const emit = defineEmits(["deleted"]);

const analystDataStore = useAnalystDataStore();
const { status } = storeToRefs(analystDataStore);

// Deleting a node deletes its replies too, so say so before it happens.
const replyCount = computed(() => {
  const count = (nodes) =>
    (nodes ?? []).reduce(
      (total, child) =>
        total +
        1 +
        count(child.notes) +
        count(child.opinions) +
        count(child.relationships),
      0,
    );

  if (!props.node) return 0;
  return (
    count(props.node.notes) +
    count(props.node.opinions) +
    count(props.node.relationships)
  );
});

async function onSubmit() {
  try {
    await analystDataStore.delete(props.node.uuid);
    emit("deleted", props.node);
    props.modal?.hide();
  } catch {
    // the store holds the error, which the template renders
  }
}
</script>

<template>
  <div :id="id" class="modal fade" tabindex="-1" aria-hidden="true">
    <div class="modal-dialog modal-dialog-centered">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title">Delete {{ node?.analyst_type }}</h5>
          <button
            type="button"
            class="btn-close"
            data-bs-dismiss="modal"
            aria-label="Discard"
          ></button>
        </div>
        <div class="modal-body">
          <p class="mb-0">
            Are you sure you want to delete this
            {{ node?.analyst_type?.toLowerCase() }}?
          </p>
          <p v-if="replyCount > 0" class="alert alert-warning mt-3 mb-0">
            This will also delete
            {{ replyCount }}
            {{ replyCount === 1 ? "reply" : "replies" }} nested under it.
          </p>
          <div v-if="status.error" class="alert alert-danger mt-3 mb-0">
            {{ status.error }}
          </div>
        </div>
        <div class="modal-footer">
          <button
            type="button"
            data-bs-dismiss="modal"
            class="btn btn-secondary"
          >
            Discard
          </button>
          <button
            type="submit"
            class="btn btn-danger"
            :class="{ disabled: status.deleting }"
            @click="onSubmit"
          >
            <span
              v-if="status.deleting"
              class="spinner-border spinner-border-sm"
              role="status"
              aria-hidden="true"
            ></span>
            <span v-else>Delete</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
