<script setup>
import { ref, computed } from "vue";
import { useModulesStore } from "@/stores";
import { storeToRefs } from "pinia";

const modulesStore = useModulesStore();
const { status, moduleResponse } = storeToRefs(modulesStore);

const props = defineProps(["module", "modal"]);

const request = ref({
  module: props.module.name,
  attribute: {
    type: "ip-dst",
    uuid: "",
    value: "8.8.8.8",
  },
});
const requestJson = ref(JSON.stringify(request.value, null, 2));

function queryModule() {
  return modulesStore
    .query(request.value)
    .catch((error) => (status.error = error));
}

const responseJson = computed(() => {
  return JSON.stringify(moduleResponse.value, null, 2);
});

function copyToClipboard(text) {
  navigator.clipboard.writeText(text);
}
</script>

<template>
  <div
    v-if="module"
    id="queryModuleModal"
    class="modal"
    aria-labelledby="queryModuleModal"
    aria-hidden="true"
  >
    <div class="modal-dialog modal-xl">
      <div v-if="module" class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title">{{ module.name }}</h5>
          <button
            type="button"
            class="btn-close"
            data-bs-dismiss="modal"
            aria-label="Discard"
          ></button>
        </div>
        <div class="modal-body">
          <div class="container mt-2">
            <div class="row">
              <!-- API Request Column -->
              <div class="col-md-6">
                <div class="mb-3">
                  <label for="request" class="form-label"
                    >request payload</label
                  >
                  <textarea
                    class="form-control"
                    id="request"
                    v-model="requestJson"
                    rows="10"
                    cols="40"
                  ></textarea>
                </div>
                <button
                  type="button"
                  class="btn btn-outline-secondary"
                  @click="copyToClipboard(requestJson)"
                >
                  <font-awesome-icon
                    class="text-secondary"
                    icon="fa-solid fa-copy"
                    @click="copyToClipboard(requestJson)"
                  />
                </button>
              </div>

              <!-- API Response Column -->
              <div class="col-md-6">
                <div class="mb-3">
                  <label for="response" class="form-label"
                    >module response</label
                  >
                  <textarea
                    class="form-control"
                    id="response"
                    rows="10"
                    placeholder="module response will be shown here"
                    v-model="responseJson"
                    readonly
                  ></textarea>
                </div>
                <button
                  type="button"
                  class="btn btn-outline-secondary"
                  @click="copyToClipboard(responseJson)"
                >
                  <font-awesome-icon
                    class="text-secondary"
                    icon="fa-solid fa-copy"
                  />
                </button>
              </div>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button
            id="closeModalButton"
            type="button"
            data-bs-dismiss="modal"
            class="btn btn-outline-secondary"
          >
            Close
          </button>
          <button
            type="submit"
            @click="queryModule"
            class="btn btn-primary"
            :class="{ disabled: status.loading }"
          >
            <span v-if="status.loading">
              <span
                class="spinner-border spinner-border-sm"
                role="status"
                aria-hidden="true"
              ></span>
            </span>
            <span v-if="!status.loading"
              ><font-awesome-icon icon="fa-solid fa-play" class="fa-lg"
            /></span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
