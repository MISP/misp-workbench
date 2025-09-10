<script setup>
import { useOrganisationsStore } from "@/stores";
import { storeToRefs } from "pinia";

const organisationsStore = useOrganisationsStore();
const { status } = storeToRefs(organisationsStore);

const props = defineProps(["organisation_uuid", "modal"]);
const emit = defineEmits(["organisation-deleted"]);

function onSubmit() {
  return organisationsStore
    .delete(props.organisation_uuid)
    .then(() => {
      emit("organisation-deleted", {
        organisation_uuid: props.organisation_uuid,
      });
      props.modal.hide();
    })
    .catch((error) => (status.error = error));
}
</script>

<template>
  <div
    :id="'deleteOrganisationModal_' + organisation_uuid"
    class="modal fade"
    tabindex="-1"
    aria-labelledby="deleteOrganisationModal"
    aria-hidden="true"
  >
    <div class="modal-dialog modal-lg">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title" id="deleteOrganisationModal">
            Delete Organisation #{{ organisation_uuid }}
          </h5>
          <button
            type="button"
            class="btn-close"
            data-bs-dismiss="modal"
            aria-label="Discard"
          ></button>
        </div>
        <div class="modal-body">
          Are you sure you want to delete this organisation?
        </div>
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
