<script setup>
import { useRolesStore } from "@/stores";
import { storeToRefs } from "pinia";

const rolesStore = useRolesStore();
const { status } = storeToRefs(rolesStore);

const props = defineProps(["role_id", "role_name", "modal"]);
const emit = defineEmits(["role-deleted"]);

function onSubmit() {
  return rolesStore
    .delete(props.role_id)
    .then(() => {
      emit("role-deleted", { role_id: props.role_id });
      props.modal.hide();
    })
    .catch((error) => (status.value.error = error));
}
</script>

<template>
  <div
    :id="'deleteRoleModal_' + role_id"
    class="modal fade"
    tabindex="-1"
    aria-hidden="true"
  >
    <div class="modal-dialog">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title">Delete Role</h5>
          <button
            type="button"
            class="btn-close"
            data-bs-dismiss="modal"
            aria-label="Discard"
          ></button>
        </div>
        <div class="modal-body">
          Are you sure you want to delete role <strong>{{ role_name }}</strong
          >?
        </div>
        <div v-if="status.error" class="alert alert-danger mx-3">
          {{ status.error }}
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
            @click="onSubmit"
            class="btn btn-outline-danger"
            :class="{ disabled: status.loading }"
          >
            <span
              v-if="status.loading"
              class="spinner-border spinner-border-sm"
              role="status"
            ></span>
            <span v-else>Delete</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
