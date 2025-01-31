<script setup>
import { useTaxonomiesStore } from "@/stores";
import { storeToRefs } from "pinia";

const taxonomiesStore = useTaxonomiesStore();
const { status } = storeToRefs(taxonomiesStore);

const props = defineProps(["taxonomy_id", "modal"]);
const emit = defineEmits(["taxonomy-deleted"]);

function deleteTaxonomy() {
  return taxonomiesStore
    .delete(props.taxonomy_id)
    .then(() => {
      emit("taxonomy-deleted", { taxonomy_id: props.taxonomy_id });
      props.modal.hide();
    })
    .catch((error) => (status.error = error));
}
</script>

<template>
  <div :id="`deleteTaxonomyModal_${taxonomy_id}`" class="modal">
    <div class="modal-dialog modal-lg">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title">Delete Taxonomy #{{ taxonomy_id }}</h5>
          <button
            type="button"
            class="btn-close"
            data-bs-dismiss="modal"
            aria-label="Discard"
          ></button>
        </div>
        <div class="modal-body">
          Are you sure you want to delete this taxonomy?
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
            @click="deleteTaxonomy"
            class="btn btn-danger"
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
