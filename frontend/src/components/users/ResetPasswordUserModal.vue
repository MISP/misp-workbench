<script setup>
import { ref } from "vue";
import { useUsersStore } from "@/stores";
import { storeToRefs } from "pinia";

const usersStore = useUsersStore();
const { status } = storeToRefs(usersStore);

const props = defineProps(["user_id", "modal"]);
const emit = defineEmits(["password-reset"]);

const password = ref("");

function onSubmit() {
  return usersStore
    .resetPassword(props.user_id, password.value || null)
    .then(() => {
      emit("password-reset", { user_id: props.user_id });
      password.value = "";
      props.modal?.hide();
    })
    .catch((error) => (status.error = error));
}
</script>

<template>
  <div
    :id="`resetPasswordUserModal-${user_id}`"
    class="modal fade"
    tabindex="-1"
    aria-labelledby="resetPasswordUserModal"
    aria-hidden="true"
  >
    <div class="modal-dialog">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title" id="resetPasswordUserModal">
            Reset Password for User #{{ user_id }}
          </h5>
          <button
            type="button"
            class="btn-close"
            data-bs-dismiss="modal"
            aria-label="Discard"
          ></button>
        </div>
        <div class="modal-body">
          <label for="new-password" class="form-label d-block text-start"
            >New Password</label
          >
          <input
            id="new-password"
            v-model="password"
            type="password"
            class="form-control"
            autocomplete="new-password"
          />
          <div class="alert alert-info small mt-2 mb-0">
            Leave empty to generate a random password and send it by email.
          </div>
        </div>
        <div v-if="status.error" class="w-100 alert alert-danger mt-3 mb-3">
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
            class="btn btn-outline-primary"
            :class="{ disabled: status.loading }"
          >
            <span v-if="status.loading">
              <span
                class="spinner-border spinner-border-sm"
                role="status"
                aria-hidden="true"
              ></span>
            </span>
            <span v-else>Reset Password</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
