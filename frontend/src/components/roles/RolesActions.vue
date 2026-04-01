<script setup>
import { authHelper } from "@/helpers";
import { ref, computed, onMounted, onBeforeUnmount } from "vue";
import { Modal } from "bootstrap";
import { storeToRefs } from "pinia";
import { useAuthStore } from "@/stores";
import DeleteRoleModal from "@/components/roles/DeleteRoleModal.vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faTrash, faEye, faPen } from "@fortawesome/free-solid-svg-icons";

const authStore = useAuthStore();
const { scopes } = storeToRefs(authStore);

const props = defineProps({
  role_id: Number,
  role_name: String,
  default_actions: {
    type: Object,
    default: () => ({}),
  },
});

const actions = computed(() => ({
  view:
    props.default_actions.view ??
    authHelper.hasScope(scopes.value, "roles:read"),
  update:
    props.default_actions.update ??
    authHelper.hasScope(scopes.value, "roles:update"),
  delete:
    props.default_actions.delete ??
    authHelper.hasScope(scopes.value, "roles:delete"),
}));

const deleteModal = ref(null);

onMounted(() => {
  deleteModal.value = new Modal(
    document.getElementById(`deleteRoleModal_${props.role_id}`),
  );
});

onBeforeUnmount(() => {
  deleteModal.value?.dispose();
});

function openDeleteModal() {
  deleteModal.value?.show();
}

const emit = defineEmits(["role-deleted"]);

function handleRoleDeleted(event) {
  emit("role-deleted", event);
}
</script>

<template>
  <div class="btn-group" role="group">
    <RouterLink
      v-if="actions.view"
      :to="`/roles/${role_id}`"
      class="btn btn-outline-primary btn-sm"
      title="View Role"
    >
      <FontAwesomeIcon :icon="faEye" fixed-width />
    </RouterLink>
    <RouterLink
      v-if="actions.update"
      :to="`/roles/update/${role_id}`"
      class="btn btn-outline-primary btn-sm"
      title="Edit Role"
    >
      <FontAwesomeIcon :icon="faPen" fixed-width />
    </RouterLink>
    <button
      v-if="actions.delete"
      type="button"
      class="btn btn-danger btn-sm"
      title="Delete Role"
      @click="openDeleteModal"
    >
      <FontAwesomeIcon :icon="faTrash" fixed-width />
    </button>
  </div>

  <DeleteRoleModal
    :role_id="role_id"
    :role_name="role_name"
    :modal="deleteModal"
    @role-deleted="handleRoleDeleted"
  />
</template>
