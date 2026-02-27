<script setup>
import { ref } from "vue";
import { RouterLink } from "vue-router";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import {
  faPen,
  faPlay,
  faPause,
  faTrash,
  faEye,
} from "@fortawesome/free-solid-svg-icons";
import { useHuntsStore, useToastsStore } from "@/stores";

const props = defineProps({
  hunt: { type: Object, required: true },
});

const emit = defineEmits(["deleted", "ran", "toggled"]);

const huntsStore = useHuntsStore();
const toastsStore = useToastsStore();

const toggling = ref(false);
const deleting = ref(false);

async function toggleStatus() {
  toggling.value = true;
  const newStatus = props.hunt.status === "active" ? "paused" : "active";
  await huntsStore
    .update(props.hunt.id, { status: newStatus })
    .then((updated) => {
      toastsStore.push(`Hunt "${props.hunt.name}" ${newStatus}.`, "success");
      emit("toggled", updated);
    })
    .catch((err) => toastsStore.push(err || "Failed to update hunt.", "danger"))
    .finally(() => (toggling.value = false));
}

async function deleteHunt() {
  if (!confirm(`Delete hunt "${props.hunt.name}"?`)) return;
  deleting.value = true;
  await huntsStore
    .delete(props.hunt.id)
    .then(() => {
      toastsStore.push(`Hunt "${props.hunt.name}" deleted.`, "success");
      emit("deleted");
    })
    .catch((err) => toastsStore.push(err || "Failed to delete hunt.", "danger"))
    .finally(() => (deleting.value = false));
}
</script>

<style scoped>
.btn-toolbar {
  display: flex;
  gap: 0.25rem;
}

@media (max-width: 576px) {
  .btn-toolbar {
    flex-wrap: wrap !important;
    width: 100%;
  }

  .btn-group,
  .btn-group-vertical {
    width: 100%;
  }

  .btn-group .btn,
  .btn-group-vertical .btn {
    width: 100%;
    justify-content: center;
  }
}
</style>

<template>
  <div
    v-if="!$isMobile"
    class="btn-toolbar d-flex align-items-center flex-nowrap float-end"
    role="toolbar"
  >
    <div class="btn-group btn-group-sm me-2" role="group">
      <button
        class="btn btn-sm"
        :class="
          hunt.status === 'active'
            ? 'btn-outline-warning'
            : 'btn-outline-success'
        "
        :title="hunt.status === 'active' ? 'Pause hunt' : 'Activate hunt'"
        :disabled="toggling"
        @click="toggleStatus"
      >
        <FontAwesomeIcon :icon="hunt.status === 'active' ? faPause : faPlay" />
      </button>
    </div>
    <div class="btn-group btn-group-sm me-2" role="group">
      <RouterLink
        :to="`/hunts/${hunt.id}`"
        class="btn btn-outline-primary btn-sm"
        title="View Hunt"
      >
        <FontAwesomeIcon :icon="faEye" />
      </RouterLink>
      <RouterLink
        :to="`/hunts/update/${hunt.id}`"
        class="btn btn-outline-primary btn-sm"
        title="Edit"
      >
        <FontAwesomeIcon :icon="faPen" />
      </RouterLink>
      <button
        class="btn btn-outline-danger btn-sm"
        title="Delete"
        :disabled="deleting"
        @click="deleteHunt"
      >
        <FontAwesomeIcon :icon="faTrash" />
      </button>
    </div>
  </div>
</template>
