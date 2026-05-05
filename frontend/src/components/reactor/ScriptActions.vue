<script setup>
import { ref, computed } from "vue";
import { storeToRefs } from "pinia";
import { RouterLink } from "vue-router";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import {
  faPen,
  faTrash,
  faEye,
  faPlay,
  faPause,
} from "@fortawesome/free-solid-svg-icons";
import { useReactorStore, useAuthStore, useToastsStore } from "@/stores";
import { authHelper } from "@/helpers";

const props = defineProps({
  script: { type: Object, required: true },
});

const emit = defineEmits(["deleted", "updated"]);

const reactorStore = useReactorStore();
const authStore = useAuthStore();
const toastsStore = useToastsStore();
const { scopes } = storeToRefs(authStore);

const canUpdate = computed(() =>
  authHelper.hasScope(scopes.value, "reactor:update"),
);
const canDelete = computed(() =>
  authHelper.hasScope(scopes.value, "reactor:delete"),
);

const deleting = ref(false);
const togglingStatus = ref(false);
const localStatus = ref(props.script.status);

const isActive = computed(
  () => (localStatus.value ?? props.script.status) === "active",
);

async function toggleStatus() {
  const nextStatus = isActive.value ? "paused" : "active";
  togglingStatus.value = true;
  await reactorStore
    .update(props.script.id, { status: nextStatus })
    .then((updated) => {
      localStatus.value = updated?.status ?? nextStatus;
      toastsStore.push(
        `Reactor script "${props.script.name}" ${
          nextStatus === "active" ? "enabled" : "paused"
        }.`,
        "success",
      );
      emit("updated", updated);
    })
    .catch((err) =>
      toastsStore.push(err || "Failed to update reactor script.", "danger"),
    )
    .finally(() => (togglingStatus.value = false));
}

async function deleteScript() {
  if (!confirm(`Delete reactor script "${props.script.name}"?`)) return;
  deleting.value = true;
  await reactorStore
    .delete(props.script.id)
    .then(() => {
      toastsStore.push(
        `Reactor script "${props.script.name}" deleted.`,
        "success",
      );
      emit("deleted");
    })
    .catch((err) =>
      toastsStore.push(err || "Failed to delete reactor script.", "danger"),
    )
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
    <div v-if="canUpdate" class="btn-group btn-group-sm me-2" role="group">
      <button
        class="btn btn-sm me"
        :class="isActive ? 'btn-outline-warning' : 'btn-outline-success'"
        :title="isActive ? 'Pause' : 'Enable'"
        :disabled="togglingStatus"
        @click="toggleStatus"
      >
        <FontAwesomeIcon :icon="isActive ? faPause : faPlay" />
      </button>
    </div>
    <div class="btn-group btn-group-sm me-2" role="group">
      <RouterLink
        :to="`/tech-lab/reactor/${script.id}`"
        class="btn btn-outline-primary btn-sm"
        title="View Reactor Script"
      >
        <FontAwesomeIcon :icon="faEye" />
      </RouterLink>
      <RouterLink
        v-if="canUpdate"
        :to="`/tech-lab/reactor/update/${script.id}`"
        class="btn btn-outline-primary btn-sm"
        title="Edit"
      >
        <FontAwesomeIcon :icon="faPen" />
      </RouterLink>
      <button
        v-if="canDelete"
        class="btn btn-outline-danger btn-sm"
        title="Delete"
        :disabled="deleting"
        @click="deleteScript"
      >
        <FontAwesomeIcon :icon="faTrash" />
      </button>
    </div>
  </div>
</template>
