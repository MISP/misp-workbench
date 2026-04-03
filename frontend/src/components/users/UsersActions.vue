<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from "vue";
import { Modal } from "bootstrap";
import { RouterLink } from "vue-router";
import { storeToRefs } from "pinia";
import { useAuthStore } from "@/stores";
import { authHelper } from "@/helpers";
import DeleteUserModal from "@/components/users/DeleteUserModal.vue";
import ResetPasswordUserModal from "@/components/users/ResetPasswordUserModal.vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import {
  faTrash,
  faEye,
  faPen,
  faKey,
} from "@fortawesome/free-solid-svg-icons";

const authStore = useAuthStore();
const { scopes } = storeToRefs(authStore);

const props = defineProps({
  user: {
    type: Object,
    required: true,
  },
  default_actions: {
    type: Object,
    default: () => ({}),
  },
});

const actions = computed(() => ({
  view:
    props.default_actions.view ??
    authHelper.hasScope(scopes.value, "users:read"),
  update:
    props.default_actions.update ??
    authHelper.hasScope(scopes.value, "users:update"),
  delete:
    props.default_actions.delete ??
    authHelper.hasScope(scopes.value, "users:delete"),
  resetPassword:
    props.default_actions.resetPassword ??
    authHelper.hasScope(scopes.value, "users:update"),
}));

const emit = defineEmits(["user-deleted"]);

const deleteModal = ref(null);
const resetPasswordModal = ref(null);

onMounted(() => {
  deleteModal.value = new Modal(
    document.getElementById(`deleteUserModal-${props.user.id}`),
  );
  resetPasswordModal.value = new Modal(
    document.getElementById(`resetPasswordUserModal-${props.user.id}`),
  );
});

onBeforeUnmount(() => {
  deleteModal.value?.dispose();
  resetPasswordModal.value?.dispose();
});

function openDeleteModal() {
  deleteModal.value?.show();
}

function openResetPasswordModal() {
  resetPasswordModal.value?.show();
}

function handleUserDeleted(event) {
  emit("user-deleted", event);
}
</script>

<template>
  <div v-if="actions.resetPassword" class="btn-group me-2" role="group">
    <button
      type="button"
      class="btn btn-outline-warning btn-sm"
      title="Reset Password"
      @click="openResetPasswordModal"
    >
      <FontAwesomeIcon :icon="faKey" fixed-width />
    </button>
  </div>
  <div class="btn-group" role="group">
    <RouterLink
      v-if="actions.view"
      :to="`/users/${user.id}`"
      class="btn btn-outline-primary btn-sm"
      title="View User"
    >
      <FontAwesomeIcon :icon="faEye" fixed-width />
    </RouterLink>
    <RouterLink
      v-if="actions.update"
      :to="`/users/update/${user.id}`"
      class="btn btn-outline-primary btn-sm"
      title="Edit User"
    >
      <FontAwesomeIcon :icon="faPen" fixed-width />
    </RouterLink>
    <button
      v-if="actions.delete"
      type="button"
      class="btn btn-danger btn-sm"
      title="Delete User"
      @click="openDeleteModal"
    >
      <FontAwesomeIcon :icon="faTrash" fixed-width />
    </button>
  </div>

  <DeleteUserModal :user_id="user.id" @user-deleted="handleUserDeleted" />
  <ResetPasswordUserModal :user_id="user.id" :modal="resetPasswordModal" />
</template>
