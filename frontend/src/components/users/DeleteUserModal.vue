<script setup>
import { useUsersStore } from "@/stores";
import { storeToRefs } from "pinia";
import * as Yup from "yup";

const usersStore = useUsersStore();
const { status } = storeToRefs(usersStore);

const props = defineProps(["user_id"]);
const emit = defineEmits(["user-deleted"]);

function onSubmit() {
  return usersStore
    .delete(props.user_id)
    .then((response) => {
      emit("user-deleted", { user_id: props.user_id });
      document.getElementById("closeModalButton").click();
    })
    .catch((error) => (status.error = error));
}
</script>

<template>
  <div
    :id="'deleteUserModal-' + user_id"
    class="modal fade"
    tabindex="-1"
    aria-labelledby="deleteUserModal"
    aria-hidden="true"
  >
    <div class="modal-dialog modal-lg">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title" id="deleteUserModal">
            Delete User #{{ user_id }}
          </h5>
          <button
            type="button"
            class="btn-close"
            data-bs-dismiss="modal"
            aria-label="Discard"
          ></button>
        </div>
        <div class="modal-body">Are you sure you want to delete this user?</div>
        <div v-if="status.error" class="w-100 alert alert-danger mt-3 mb-3">
          {{ status.error }}
        </div>
        <div class="modal-footer">
          <button
            id="closeModalButton"
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
            <span v-if="status.loading">
              <span
                class="spinner-border spinner-border-sm"
                role="status"
                aria-hidden="true"
              ></span>
            </span>
            <span v-if="!status.loading">Delete</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
