<script setup>
import { ref, watch } from "vue";
import { useObjectsStore } from "@/stores";
import { errorHandler } from "@/helpers";
import { storeToRefs } from "pinia";
import { DISTRIBUTION_LEVEL } from "@/helpers/constants";
import ObjectTemplateSelect from "@/components/enums/ObjectTemplateSelect.vue";
import ApiError from "@/components/misc/ApiError.vue";
import AddObjectAttributesForm from "@/components/objects/AddObjectAttributesForm.vue";
import AddObjectPreview from "@/components/objects/AddObjectPreview.vue";
import DisplayObjectTemplate from "@/components/objects/DisplayObjectTemplate.vue";
import { objectTemplatesHelper } from "@/helpers";
import { Form } from "vee-validate";

const objectsStore = useObjectsStore();
const { status } = storeToRefs(objectsStore);
const apiError = ref(null);
const objectTemplateErrors = ref(null);
const props = defineProps(["event_uuid", "modal"]);
const emit = defineEmits(["object-created"]);

function createEmptyObject() {
  return {
    distribution: DISTRIBUTION_LEVEL.INHERIT_EVENT,
    meta_category: "network",
    template_uuid: null,
    attributes: [],
    deleted: false,
    event_uuid: props.event_uuid,
  };
}

function createEmptyTemplate() {
  return {
    uuid: "",
    name: "",
    version: "",
    requiredOneOf: [],
  };
}

const object = ref(createEmptyObject());
const resetVeeForm = ref(null);
const selectedQuickTemplate = ref("");
const activeTemplate = ref(createEmptyTemplate());

const defaultObjectTemplates = {
  "domain/ip": "43b3b146-77eb-4931-b4cc-b66c60f28734",
  "url/domain": "60efb77b-40b5-4c46-871b-ed1ed999fce5",
  "file/hash": "688c46fb-5edb-40a3-8273-1af7923e2215",
  vulnerability: "81650945-f186-437b-8945-9f31715d32da",
  financial: "c51ed099-a628-46ee-ad8f-ffed866b6b8d",
  personal: "a15b0477-e9d1-4b9c-9546-abe78a4f4248",
};

const templateIconMap = {
  "domain/ip": "fa-network-wired",
  "url/domain": "fa-link",
  "file/hash": "fa-file-lines",
  vulnerability: "fa-bug",
  financial: "fa-money-check-dollar",
  personal: "fa-person",
};

const selectTemplateByUuid = (uuid) => {
  object.value.template_uuid = uuid;
  const template = objectsStore.getObjectTemplateByUuid(uuid);
  console.log("Selected template:", template);
  if (template) {
    activeTemplate.value = template;
  } else {
    activeTemplate.value = createEmptyTemplate();
  }
  selectedQuickTemplate.value = "";
};

watch(selectedQuickTemplate, (newValue) => {
  if (defaultObjectTemplates[newValue]) {
    selectTemplateByUuid(defaultObjectTemplates[newValue]);
  }
});

function handleAttributesUpdated() {
  objectTemplatesHelper
    .validateObject(activeTemplate.value, object.value)
    .then(() => {
      objectTemplateErrors.value = null;
    })
    .catch((error) => {
      objectTemplateErrors.value = error;
    });
}

function createObject(values, { setErrors }) {
  object.value.name = activeTemplate.value.name;
  object.value.template_version = activeTemplate.value.version;
  object.value.deleted = false;
  object.value.timestamp = parseInt(Date.now() / 1000);

  objectTemplatesHelper
    .validateObject(activeTemplate.value, object.value)
    .then(() => {
      return objectsStore
        .create(object.value)
        .then((response) => {
          emit("object-created", { object: response });
          resetObjectModal();
          props.modal.hide();
        })
        .catch((errors) => {
          apiError.value = errors;
          setErrors(errorHandler.transformApiToFormErrors(errors));
        });
    })
    .catch((errors) => {
      objectTemplateErrors.value = errors;
    });
}

function resetObjectModal() {
  object.value = createEmptyObject();
  activeTemplate.value = createEmptyTemplate();
  selectedQuickTemplate.value = "";

  apiError.value = null;
  objectTemplateErrors.value = null;

  if (resetVeeForm.value) {
    resetVeeForm.value();
  }
}

function onClose() {
  resetObjectModal();
  props.modal.hide();
}

function handleObjectTemplateUpdated(templateUuid) {
  selectTemplateByUuid(templateUuid);
  objectTemplateErrors.value = null;
}
</script>

<style>
.modal-body {
  max-height: 70vh;
  overflow-y: auto;
  padding-right: 1rem;
  /* prevent scrollbar overlaying content */
}

.section {
  margin-bottom: 2rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid var(--bs-border-color);
}

.section:last-child {
  border-bottom: none;
}

.template-card {
  transition: all 0.15s ease;
  cursor: pointer;
}

.template-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.1);
}

.template-card.border-primary {
  border-width: 2px !important;
}

.template-list {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
}

.template-list > div {
  flex: 1 0 12rem;
  max-width: 12rem;
}
</style>

<template>
  <div
    id="addObjectModal"
    class="modal fade"
    aria-labelledby="addObjectModalLabel"
    aria-hidden="true"
    tabindex="-1"
  >
    <Form @submit="createObject" v-slot="{ errors, resetForm }">
      <template v-if="!resetVeeForm">{{ resetVeeForm = resetForm }}</template>
      <div class="modal-dialog modal-xl">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title" id="addObjectModalLabel">Add Object</h5>
            <button
              type="button"
              class="btn-close btn-outline-s"
              data-bs-dismiss="modal"
              aria-label="Discard"
              @click="onClose()"
            />
          </div>
          <div class="modal-body">
            <!-- Category / Template Selection -->
            <section class="section" id="category-section">
              <h4>Choose Object Template</h4>
              <div class="row g-3 mx-0">
                <div
                  v-for="(uuid, key) in defaultObjectTemplates"
                  :key="key"
                  class="col-6 col-md-2 px-2"
                >
                  <div
                    class="card h-100 template-card"
                    :class="{ 'border-primary': activeTemplate.uuid === uuid }"
                    role="button"
                    @click="selectTemplateByUuid(uuid)"
                  >
                    <div class="card-body text-center">
                      <font-awesome-icon
                        :icon="templateIconMap[key]"
                        class="fa-2xl mb-3"
                      />
                      <h6 class="card-title text-capitalize">
                        {{ key.replace("/", " / ") }}
                      </h6>
                    </div>
                  </div>
                </div>
              </div>

              <hr class="my-4" />

              <div>
                <h5>Or choose from all templates</h5>
                <ObjectTemplateSelect
                  name="activeTemplate"
                  :selected="activeTemplate"
                  @object-template-updated="handleObjectTemplateUpdated"
                  :errors="errors['activeTemplate']"
                />
              </div>

              <div v-if="activeTemplate.uuid" class="mt-4">
                <div class="alert alert-success d-flex align-items-center">
                  <font-awesome-icon icon="fa-check-circle" class="me-2" />
                  <strong class="me-2">Selected template:</strong>
                  {{ activeTemplate.name }}
                </div>

                <DisplayObjectTemplate
                  :key="activeTemplate.uuid"
                  :template="activeTemplate"
                />
              </div>
            </section>

            <!-- Attributes -->
            <section
              class="section"
              id="attributes-section"
              v-if="activeTemplate.uuid"
            >
              <h4>Attributes</h4>
              <AddObjectAttributesForm
                :object="object"
                :template="activeTemplate"
                :key="activeTemplate.uuid"
                @object-attribute-added="handleAttributesUpdated"
                @object-attribute-deleted="handleAttributesUpdated"
              />
            </section>

            <!-- Preview -->
            <section
              class="section"
              id="preview-section"
              v-if="activeTemplate.uuid"
            >
              <h4>Preview</h4>
              <AddObjectPreview :object="object" :template="activeTemplate" />
            </section>
          </div>

          <div v-if="apiError" class="w-100 alert alert-danger mt-3 mb-3">
            <ApiError :errors="apiError" />
          </div>
          <div
            v-if="objectTemplateErrors"
            class="w-100 alert alert-danger mt-3 mb-3"
          >
            <span>{{ objectTemplateErrors }}</span>
          </div>

          <div class="modal-footer">
            <button
              type="button"
              data-bs-dismiss="modal"
              class="btn btn-outline-secondary"
              @click="onClose()"
            >
              Discard
            </button>
            <button
              type="submit"
              class="btn btn-primary"
              :disabled="status.loading || !activeTemplate.uuid"
            >
              <span v-show="status.loading">
                <span
                  class="spinner-border spinner-border-sm"
                  role="status"
                  aria-hidden="true"
                />
              </span>
              <span v-show="!status.loading">Add Object</span>
            </button>
          </div>
        </div>
      </div>
    </Form>
  </div>
</template>
