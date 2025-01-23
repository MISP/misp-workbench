<script setup>
import { ref, watch } from "vue";
import { useObjectsStore } from "@/stores";
import { errorHandler } from "@/helpers";
import { storeToRefs } from "pinia";
import { ObjectSchema } from "@/schemas/object";
import { DISTRIBUTION_LEVEL } from "@/helpers/constants";
import ObjectTemplateSelect from "@/components/enums/ObjectTemplateSelect.vue";
import ApiError from "@/components/misc/ApiError.vue";
import AddObjectAttributesForm from "@/components/objects/AddObjectAttributesForm.vue";
import AddObjectPreview from "@/components/objects/AddObjectPreview.vue";
import DisplayObjectTemplate from "@/components/objects/DisplayObjectTemplate.vue";
import { Form } from "vee-validate";
import * as Yup from "yup";

const objectsStore = useObjectsStore();
const { status } = storeToRefs(objectsStore);
const apiError = ref(null);
const objectTemplateErrors = ref(null);
const props = defineProps(["event_id", "modal"]);
const emit = defineEmits(["object-created"]);

const object = ref({
  distribution: DISTRIBUTION_LEVEL.INHERIT_EVENT,
  meta_category: "network",
  template_uuid: null,
  attributes: [],
  deleted: false,
  event_id: props.event_id,
});

const selectedQuickTemplate = ref("");
const activeTemplate = ref({
  requiredOneOf: [],
});

function getObjectTemplateSchema() {
  return Yup.object().shape({
    attributes: Yup.array().test(
      "at-least-one-required-type",
      `The object must contain at least one attribute with a type matching one of the following: ${activeTemplate.value.requiredOneOf.join(
        ", ",
      )}`,
      (attributes) =>
        attributes &&
        attributes.some((attribute) =>
          activeTemplate.value.requiredOneOf.includes(attribute.template_type),
        ),
    ),
  });
}

const validateObject = (object) => {
  return new Promise((resolve, reject) => {
    const schema = getObjectTemplateSchema();
    ObjectSchema.concat(schema)
      .validate(object)
      .then((validObject) => {
        objectTemplateErrors.value = null;
        resolve(validObject);
      })
      .catch((error) => {
        objectTemplateErrors.value = error;
        reject(error);
      });
  });
};

function handleAttributesUpdated() {
  validateObject(object.value)
    .then((validObject) => {
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

  validateObject(object.value)
    .then((validObject) => {
      return objectsStore
        .create(object.value)
        .then((response) => {
          emit("object-created", { object: response });
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

function onClose() {
  object.value = {
    distribution: DISTRIBUTION_LEVEL.INHERIT_EVENT,
    meta_category: "network",
    template_uuid: null,
    template: null,
  };
  props.modal.hide();
}

function handleObjectTemplateUpdated(templateUuid) {
  object.value.template_uuid = templateUuid;
  activeTemplate.value = objectsStore.getObjectTemplateByUuid(templateUuid);
  ObjectTemplateSchema.value = getObjectTemplateSchema();

  validateObjectTemplate();

  selectedQuickTemplate.value = "";
}

const defaultObjectTemplates = {
  "domain/ip": "43b3b146-77eb-4931-b4cc-b66c60f28734",
  "url/domain": "60efb77b-40b5-4c46-871b-ed1ed999fce5",
  "file/hash": "688c46fb-5edb-40a3-8273-1af7923e2215",
  vulnerability: "81650945-f186-437b-8945-9f31715d32da",
  financial: "c51ed099-a628-46ee-ad8f-ffed866b6b8d",
  personal: "a15b0477-e9d1-4b9c-9546-abe78a4f4248",
};

watch(selectedQuickTemplate, (newValue, oldValue) => {
  if (defaultObjectTemplates[newValue]) {
    object.value.template_uuid = defaultObjectTemplates[newValue];
    activeTemplate.value = objectsStore.getObjectTemplateByUuid(
      defaultObjectTemplates[newValue],
    );
  }
});
</script>

<style>
.tab-content {
  border-left: 1px solid #ddd;
  border-right: 1px solid #ddd;
  border-bottom: 1px solid #ddd;
  padding: 10px;
}

.nav-tabs {
  margin-bottom: 0;
}

.figure {
  width: 100px;
  text-align: center;
  vertical-align: middle;
}
</style>

<template>
  <div
    id="addObjectModal"
    class="modal fade"
    aria-labelledby="addObjectModalLabel"
    aria-hidden="true"
  >
    <Form @submit="createObject" v-slot="{ errors }">
      <div class="modal-dialog modal-xl">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title" id="addObjectModalLabel">Add Object</h5>
            <button
              type="button"
              class="btn-close btn-outline-s"
              data-bs-dismiss="modal"
              aria-label="Discard"
            ></button>
          </div>
          <div class="modal-body">
            <ul class="nav nav-tabs" id="addObjectTabs" role="tablist">
              <li class="nav-item" role="presentation">
                <button
                  class="nav-link active"
                  id="category-tab"
                  data-bs-toggle="tab"
                  data-bs-target="#category"
                  type="button"
                  role="tab"
                  aria-controls="category"
                  aria-selected="true"
                >
                  Category
                </button>
              </li>
              <li class="nav-item" role="presentation">
                <button
                  class="nav-link"
                  id="attributes-tab"
                  data-bs-toggle="tab"
                  :disabled="!activeTemplate.uuid"
                  data-bs-target="#attributes"
                  type="button"
                  role="tab"
                  aria-controls="attributes"
                  aria-selected="false"
                >
                  Attributes
                </button>
              </li>
              <!-- <li class="nav-item" role="presentation">
                                <button class="nav-link" id="distribution-tab" data-bs-toggle="tab"
                                    data-bs-target="#distribution" type="button" role="tab" aria-controls="distribution"
                                    aria-selected="false">Distribution</button>
                            </li> -->
              <!-- <li class="nav-item" role="presentation">
                                <button class="nav-link" id="advanced-tab" data-bs-toggle="tab"
                                    data-bs-target="#advanced" type="button" role="tab" aria-controls="advanced"
                                    aria-selected="false">Advanced</button>
                            </li> -->
              <li class="nav-item" role="presentation">
                <button
                  class="nav-link"
                  id="preview-tab"
                  data-bs-toggle="tab"
                  data-bs-target="#preview"
                  :disabled="!activeTemplate.uuid"
                  type="button"
                  role="tab"
                  aria-controls="preview"
                  aria-selected="false"
                >
                  Preview
                </button>
              </li>
            </ul>
            <div class="tab-content" id="add-object-tab-content">
              <div
                class="tab-pane show active"
                id="category"
                role="tabpanel"
                aria-labelledby="category-tab"
              >
                <div class="btn-group" role="group">
                  <input
                    type="radio"
                    class="btn-check"
                    v-model="selectedQuickTemplate"
                    v-bind:value="'domain/ip'"
                    name="btnradio"
                    id="btn-domain-ip"
                    autocomplete="off"
                  />
                  <label class="btn btn-outline-primary" for="btn-domain-ip">
                    <font-awesome-icon
                      icon="fa-solid fa-network-wired"
                      class="fa-2xl mt-3"
                    />
                    <p>Domain/IP</p>
                  </label>
                  <input
                    type="radio"
                    class="btn-check"
                    v-model="selectedQuickTemplate"
                    v-bind:value="'url/domain'"
                    name="btnradio"
                    id="btn-url-domain"
                    autocomplete="off"
                  />
                  <label class="btn btn-outline-primary" for="btn-url-domain">
                    <font-awesome-icon
                      icon="fa-solid fa-link"
                      class="fa-2xl mt-3"
                    />
                    <p>URL/Domain</p>
                  </label>
                  <input
                    type="radio"
                    class="btn-check"
                    v-model="selectedQuickTemplate"
                    v-bind:value="'file/hash'"
                    name="btnradio"
                    id="btn-file-hash"
                    autocomplete="off"
                  />
                  <label class="btn btn-outline-primary" for="btn-file-hash">
                    <font-awesome-icon
                      icon="fa-solid fa-file-lines"
                      class="fa-2xl mt-3"
                    />
                    <p>File/Hash</p>
                  </label>
                  <input
                    type="radio"
                    class="btn-check"
                    v-model="selectedQuickTemplate"
                    v-bind:value="'vulnerability'"
                    name="btnradio"
                    id="btn-vulnerability"
                    autocomplete="off"
                  />
                  <label
                    class="btn btn-outline-primary"
                    for="btn-vulnerability"
                  >
                    <font-awesome-icon
                      icon="fa-solid fa-skull-crossbones"
                      class="fa-2xl mt-3"
                    />
                    <p>Vulnerability</p>
                  </label>
                  <input
                    type="radio"
                    class="btn-check"
                    v-model="selectedQuickTemplate"
                    v-bind:value="'financial'"
                    name="btnradio"
                    id="btn-financial"
                    autocomplete="off"
                  />
                  <label class="btn btn-outline-primary" for="btn-financial">
                    <font-awesome-icon
                      icon="fa-solid fa-money-check-dollar"
                      class="fa-2xl mt-3"
                    />
                    <p>Financial</p>
                  </label>
                  <input
                    type="radio"
                    class="btn-check"
                    v-model="selectedQuickTemplate"
                    v-bind:value="'personal'"
                    name="btnradio"
                    id="btn-person"
                    autocomplete="off"
                  />
                  <label class="btn btn-outline-primary" for="btn-person">
                    <font-awesome-icon
                      icon="fa-solid fa-person"
                      class="fa-2xl mt-3"
                    />
                    <p>Personal</p>
                  </label>
                </div>
                <div class="col text-start mt-3">
                  <label for="activeTemplate" class="form-label"
                    >Or select a template from the list:</label
                  >
                  <ObjectTemplateSelect
                    name="activeTemplate"
                    :selected="activeTemplate"
                    @object-template-updated="handleObjectTemplateUpdated"
                    :errors="errors['activeTemplate']"
                  />
                  <div class="invalid-feedback">
                    {{ errors["activeTemplate"] }}
                  </div>
                </div>
                <div>
                  <DisplayObjectTemplate
                    v-if="activeTemplate.uuid"
                    :key="activeTemplate.uuid"
                    :template="activeTemplate"
                  />
                </div>
              </div>
              <div
                class="tab-pane"
                id="attributes"
                role="tabpanel"
                aria-labelledby="attributes-tab"
              >
                <AddObjectAttributesForm
                  v-if="activeTemplate.uuid"
                  :object="object"
                  :key="activeTemplate.uuid"
                  :template="activeTemplate"
                  @object-attribute-added="handleAttributesUpdated"
                  @object-attribute-deleted="handleAttributesUpdated"
                />
              </div>
              <!-- <div class="tab-pane" id="distribution" role="tabpanel" aria-labelledby="distribution-tab">
                                distribution
                            </div> -->
              <!-- <div class="tab-pane" id="advanced" role="tabpanel" aria-labelledby="advanced-tab">
                                <div class="row m-2">
                                    <div class="col col-6 text-start">
                                        <label for="object.distribution" class="form-label">distribution</label>
                                        <DistributionLevelSelect name="object.distribution"
                                            :selected=object.distribution
                                            @distribution-level-updated="handleDistributionLevelUpdated"
                                            :errors="errors['object.distribution']" />
                                        <div class="invalid-feedback">{{ errors['object.distribution'] }}</div>
                                    </div>
                                </div>
                                <div class="row m-2">
                                    <div class="col col-6 text-start">
                                        <label for="object.meta_category" class="form-label">meta-category</label>
                                        <ObjectMetaCategorySelect name="object.meta-category"
                                            :selected=object.meta_category
                                            @object-meta-category-updated="handleObjectMetaCategoryUpdated"
                                            :errors="errors['object.meta_category']" />
                                        <div class="invalid-feedback">{{ errors['object.meta_category'] }}</div>
                                    </div>
                                </div>
                                <div class="row m-2">
                                    <div class="col text-start">
                                        <label for="object.template" class="form-label">template</label>
                                        <ObjectTemplateSelect name="object.template" :selected=object.template
                                            @object-template-updated="handleObjectTemplateUpdated"
                                            :errors="errors['object.template']" />
                                        <div class="invalid-feedback">{{ errors['object.template'] }}</div>
                                    </div>
                                </div>
                            </div> -->
              <div
                class="tab-pane"
                id="preview"
                role="tabpanel"
                aria-labelledby="preview-tab"
              >
                <AddObjectPreview :object="object" :template="activeTemplate" />
              </div>
            </div>
            <!-- TODO -->
            <!--
                        <div class="row m-2">
                            <div class="col col-6 text-start">
                                <label for="objectSharingGroupId" class="form-label">Sharing Group</label>
                                <SharingGroupSelect v-model=object.sharing_group_id />
                                <div class="invalid-feedback">{{ errors['object.sharing_group_id'] }}</div>
                            </div>
                        </div> 
                        -->
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
              id="closeModalButton"
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
                ></span>
              </span>
              <span v-show="!status.loading">Add Object</span>
            </button>
          </div>
        </div>
      </div>
    </Form>
  </div>
</template>
