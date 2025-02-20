<script setup>
import { ref } from "vue";
import ApiError from "@/components/misc/ApiError.vue";
import { ObjectSchema } from "@/schemas/object";
import { Form, Field } from "vee-validate";
import AddObjectAttributesForm from "@/components/objects/AddObjectAttributesForm.vue";
import DistributionLevelSelect from "@/components/enums/DistributionLevelSelect.vue";
import DisplayObjectTemplate from "@/components/objects/DisplayObjectTemplate.vue";
import Datepicker from "@/components/misc/Datepicker.vue";
import { useObjectsStore } from "@/stores";
import { objectTemplatesHelper } from "@/helpers";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faCubesStacked } from "@fortawesome/free-solid-svg-icons";

const props = defineProps(["object", "template", "status"]);
const objectTemplateErrors = ref(null);
const apiError = ref(null);
const objectsStore = useObjectsStore();
const newAttributes = ref([]);
const updateAttributes = ref([]);
const deletedAttributes = ref([]);

const object = ref(props.object);

function handleObjectUpdated() {
  objectTemplatesHelper
    .validateObject(props.template, object.value)
    .then(() => {
      objectTemplateErrors.value = null;
    })
    .catch((error) => {
      objectTemplateErrors.value = error;
    });
}

function handleObjectAttributeAdded(event) {
  newAttributes.value.push(event.attribute);
  handleObjectUpdated(event);
}

function handleObjectAttributeUpdated(event) {
  updateAttributes.value.push(event.attribute);
  handleObjectUpdated(event);
}

function handleObjectAttributeDeleted(event) {
  if (event.attribute.uuid) {
    deletedAttributes.value.push(event.attribute.uuid);
  } else {
    newAttributes.value = newAttributes.value.filter(
      (attribute) => attribute.value !== event.attribute.value,
    );
  }
  handleObjectUpdated(event);
}

function handleDistributionLevelUpdated(distributionLevelId) {
  object.value.distribution = parseInt(distributionLevelId);
}

function updateObject() {
  objectTemplatesHelper
    .validateObject(props.template, object.value)
    .then(() => {
      return objectsStore
        .update({
          ...object.value,
          new_attributes: newAttributes.value,
          update_attributes: updateAttributes.value,
          delete_attributes: deletedAttributes.value,
        })
        .then((response) => {
          objectTemplateErrors.value = null;
          newAttributes.value = [];
          updateAttributes.value = [];
          deletedAttributes.value = [];
          object.value = response;
        })
        .catch((errors) => {
          apiError.value = errors;
        });
    })
    .catch((error) => {
      objectTemplateErrors.value = error;
    });
}
</script>
<template>
  <div class="card">
    <div class="card-header border-bottom">
      <div class="row">
        <div class="col-10">
          <h3>Update Object</h3>
        </div>
      </div>
    </div>

    <div class="card-body d-flex flex-column">
      <div>
        <DisplayObjectTemplate :template="template" />
      </div>
      <div>
        <div class="card-body d-flex flex-column">
          <Form :validation-schema="ObjectSchema" v-slot="{ errors }">
            <div class="mb-3">
              <label for="object.id">id</label>
              <Field
                class="form-control"
                id="object.id"
                name="object.id"
                v-model="object.id"
                :class="{ 'is-invalid': errors['object.id'] }"
                disabled
              >
              </Field>
              <div class="invalid-feedback">{{ errors["object.id"] }}</div>
            </div>
            <div class="mb-3">
              <label for="object.uuid">uuid</label>
              <Field
                class="form-control"
                id="object.uuid"
                name="object.uuid"
                v-model="object.uuid"
                :class="{ 'is-invalid': errors['object.uuid'] }"
                disabled
              >
              </Field>
              <div class="invalid-feedback">{{ errors["object.uuid"] }}</div>
            </div>
            <div class="mb-3">
              <label for="attribute.distribution" class="form-label"
                >distribution</label
              >
              <DistributionLevelSelect
                name="object.distribution"
                :selected="object.distribution"
                @distribution-level-updated="handleDistributionLevelUpdated"
                :errors="errors['object.distribution']"
              />
              <div class="invalid-feedback">
                {{ errors["object.distribution"] }}
              </div>
            </div>
            <div class="mb-3">
              <label for="object.timestamp">timestamp</label>
              <Datepicker
                v-model="object.timestamp"
                name="object.timestamp"
                altFormat="Z"
                dateFormat="U"
                enableTime
              />
              <div class="invalid-feedback">
                {{ errors["object.timestamp"] }}
              </div>
            </div>
            <div class="mb-3">
              <label for="object.last_seen">first seen</label>
              <Datepicker
                v-model="object.first_seen"
                name="object.first_seen"
                altFormat="Z"
                dateFormat="U"
                enableTime
              />
              <div class="invalid-feedback">
                {{ errors["object.first_seen"] }}
              </div>
            </div>
            <div class="mb-3">
              <label for="object.last_seen">last seen</label>
              <Datepicker
                v-model="object.last_seen"
                name="object.last_seen"
                altFormat="Z"
                dateFormat="U"
                enableTime
              />
              <div class="invalid-feedback">
                {{ errors["object.last_seen"] }}
              </div>
            </div>
            <div class="mb-3">
              <label for="object.comment">comment</label>
              <Field
                class="form-control"
                id="object.comment"
                name="object.comment"
                as="textarea"
                v-model="object.comment"
                style="height: 100px"
                :class="{ 'is-invalid': errors['object.comment'] }"
              >
              </Field>
              <div class="invalid-feedback">
                {{ errors["object.comment"] }}
              </div>
            </div>
            <div class="card">
              <div class="card-header">
                <FontAwesomeIcon :icon="faCubesStacked" /> attributes
              </div>
              <div class="card-body d-flex flex-column">
                <AddObjectAttributesForm
                  :object="object"
                  :key="template.uuid"
                  :template="template"
                  @object-attribute-added="handleObjectAttributeAdded"
                  @object-attribute-updated="handleObjectAttributeUpdated"
                  @object-attribute-deleted="handleObjectAttributeDeleted"
                />
              </div>
            </div>
            <div
              v-if="objectTemplateErrors"
              class="w-100 alert alert-danger mt-3 mb-3"
            >
              {{ objectTemplateErrors }}
            </div>
            <div v-if="apiError" class="w-100 alert alert-danger mt-3 mb-3">
              <ApiError :errors="apiError" />
            </div>
            <div class="text-center mt-3">
              <button
                type="submit"
                @click="updateObject"
                class="btn btn-primary"
                :disabled="status.loading || objectTemplateErrors"
              >
                <span v-show="status.loading">
                  <span
                    class="spinner-border spinner-border-sm"
                    role="status"
                    aria-hidden="true"
                  ></span>
                </span>
                <span v-show="!status.loading">Save Object</span>
              </button>
            </div>
          </Form>
        </div>
      </div>
    </div>
  </div>
</template>
