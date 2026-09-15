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
import { useServosStore, useAuthStore, useToastsStore } from "@/stores";
import { authHelper } from "@/helpers";

const props = defineProps({
  servo: { type: Object, required: true },
});

const emit = defineEmits(["deleted", "updated"]);

const servosStore = useServosStore();
const authStore = useAuthStore();
const toastsStore = useToastsStore();
const { scopes } = storeToRefs(authStore);

const canUpdate = computed(() =>
  authHelper.hasScope(scopes.value, "servos:update"),
);
const canDelete = computed(() =>
  authHelper.hasScope(scopes.value, "servos:delete"),
);

const deleting = ref(false);
const toggling = ref(false);
const localEnabled = ref(props.servo.enabled);

const isEnabled = computed(() => localEnabled.value ?? props.servo.enabled);

async function toggleEnabled() {
  const next = !isEnabled.value;
  toggling.value = true;
  await servosStore
    .update(props.servo.id, { enabled: next })
    .then((updated) => {
      localEnabled.value = updated?.enabled ?? next;
      toastsStore.push(
        `Servo "${props.servo.name}" ${next ? "enabled" : "disabled"}. ` +
          "Attributes indexed from now on are affected.",
        "success",
      );
      emit("updated", updated);
    })
    .catch((err) =>
      toastsStore.push(err || "Failed to update servo.", "danger"),
    )
    .finally(() => (toggling.value = false));
}

async function deleteServo() {
  if (
    !confirm(
      `Delete servo "${props.servo.name}"? Its ingest pipeline is removed from ` +
        "OpenSearch. Attributes it already transformed keep those fields.",
    )
  )
    return;
  deleting.value = true;
  await servosStore
    .delete(props.servo.id)
    .then(() => {
      toastsStore.push(`Servo "${props.servo.name}" deleted.`, "success");
      emit("deleted");
    })
    .catch((err) =>
      toastsStore.push(err || "Failed to delete servo.", "danger"),
    )
    .finally(() => (deleting.value = false));
}
</script>

<template>
  <div
    class="btn-toolbar d-flex align-items-center flex-nowrap float-end gap-1"
    role="toolbar"
  >
    <div v-if="canUpdate" class="btn-group btn-group-sm me-2" role="group">
      <button
        class="btn btn-sm"
        :class="isEnabled ? 'btn-outline-warning' : 'btn-outline-success'"
        :title="isEnabled ? 'Disable' : 'Enable'"
        :disabled="toggling"
        @click="toggleEnabled"
      >
        <FontAwesomeIcon :icon="isEnabled ? faPause : faPlay" />
      </button>
    </div>
    <div class="btn-group btn-group-sm" role="group">
      <RouterLink
        :to="`/tech-lab/servos/${servo.id}`"
        class="btn btn-outline-primary btn-sm"
        title="View servo"
      >
        <FontAwesomeIcon :icon="faEye" />
      </RouterLink>
      <RouterLink
        v-if="canUpdate"
        :to="`/tech-lab/servos/update/${servo.id}`"
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
        @click="deleteServo"
      >
        <FontAwesomeIcon :icon="faTrash" />
      </button>
    </div>
  </div>
</template>
