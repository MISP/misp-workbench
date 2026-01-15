<script setup>
import { watch, ref } from "vue";
import { useAttributesStore } from "@/stores";
import { errorHandler } from "@/helpers";
import { storeToRefs } from "pinia";
import { AttributeSchema } from "@/schemas/attribute";
import { DISTRIBUTION_LEVEL } from "@/helpers/constants";
import DistributionLevelSelect from "@/components/enums/DistributionLevelSelect.vue";
import ApiError from "@/components/misc/ApiError.vue";
import AttributeCategorySelect from "@/components/enums/AttributeCategorySelect.vue";
import AttributeTypeSelect from "@/components/enums/AttributeTypeSelect.vue";
import Datepicker from "@/components/misc/Datepicker.vue";
import { Form, Field } from "vee-validate";

const attributesStore = useAttributesStore();
const { status } = storeToRefs(attributesStore);
const apiError = ref(null);
const props = defineProps(["event_uuid", "modal"]);
const emit = defineEmits(["attribute-created"]);

const detected = ref(null);
const resetVeeForm = ref(null);

function createEmptyAttribute() {
  return {
    distribution: DISTRIBUTION_LEVEL.INHERIT_EVENT,
    event_uuid: props.event_uuid,
    disable_correlation: false,
    type: null,
    category: null,
    value: "",
  };
}

const attribute = ref(createEmptyAttribute());

watch(
  () => attribute.value.value,
  (newValue) => {
    const result = detectAttribute(newValue);

    if (!result) {
      detected.value = null;
      return;
    }

    detected.value = result;

    attribute.value.type = result.type;
    attribute.value.category = result.category;
  },
);

function addAttribute(values, { setErrors }) {
  apiError.value = null;
  return attributesStore
    .create(attribute.value)
    .then((response) => {
      emit("attribute-created", { attribute: response });
      onClose();
      props.modal.hide();
    })
    .catch((errors) => {
      apiError.value = errors;
      setErrors(errorHandler.transformApiToFormErrors(errors));
    });
}

function onClose() {
  attribute.value = createEmptyAttribute();
  detected.value = null;
  apiError.value = null;

  if (resetVeeForm.value) {
    resetVeeForm.value();
  }
}

function handleAttributeCategoryUpdated(category) {
  attribute.value.category = category;
}

function handleAttributeTypeUpdated(type) {
  attribute.value.type = type;
}

function handleDistributionLevelUpdated(distributionLevelId) {
  attribute.value.distribution = parseInt(distributionLevelId);
}

function detectAttribute(value) {
  if (!value) return null;

  const v = value.trim();

  // IPv4
  if (/^(?:\d{1,3}\.){3}\d{1,3}$/.test(v)) {
    return {
      type: "ip-dst",
      category: "Network activity",
      label: "IP address",
    };
  }

  // SHA-256
  if (/^[a-fA-F0-9]{64}$/.test(v)) {
    return {
      type: "sha256",
      category: "Payload delivery",
      label: "SHA-256 hash",
    };
  }

  // MD5
  if (/^[a-fA-F0-9]{32}$/.test(v)) {
    return { type: "md5", category: "Payload delivery", label: "MD5 hash" };
  }

  // URL
  if (/^https?:\/\//i.test(v)) {
    return { type: "url", category: "Payload delivery", label: "URL" };
  }

  // Domain
  if (/^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/.test(v)) {
    return { type: "domain", category: "Network activity", label: "Domain" };
  }

  // CVE / GCVE
  if (/^(?:CVE-\d{4}-\d{4,}|GCVE-0-\d{4}-\d{4,})$/i.test(v)) {
    return {
      type: "vulnerability",
      category: "External analysis",
      label: "Vulnerability",
    };
  }

  return null;
}
</script>

<template>
  <div
    id="addAttributeModal"
    class="modal"
    aria-labelledby="addAttributeModal"
    aria-hidden="true"
  >
    <div class="modal-dialog modal-lg">
      <Form
        @submit="addAttribute"
        :validation-schema="AttributeSchema"
        v-slot="{ errors, resetForm }"
      >
        <template v-if="!resetVeeForm">
          {{ resetVeeForm = resetForm }}
        </template>
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title" id="addAttributeModalLabel">
              Add Attribute
            </h5>
            <button
              type="button"
              class="btn-close"
              data-bs-dismiss="modal"
              aria-label="Discard"
            ></button>
          </div>
          <div class="modal-body">
            <div class="row m-2">
              <div class="col text-start">
                <label for="attribute.value">value</label>
                <Field
                  class="form-control"
                  id="attribute.value"
                  name="attribute.value"
                  as="textarea"
                  placeholder="IOC or data here ..."
                  v-model="attribute.value"
                  style="height: 100px"
                  :class="{ 'is-invalid': errors['attribute.value'] }"
                >
                </Field>
                <div class="invalid-feedback">
                  {{ errors["attribute.value"] }}
                </div>
              </div>
            </div>
            <div class="row m-2">
              <div class="col text-start">
                <label class="form-label">
                  type <small class="text-muted">(override if needed)</small>
                </label>
                <AttributeTypeSelect
                  name="attribute.type"
                  :key="attribute.category"
                  :category="attribute.category"
                  :selected="attribute.type"
                  @attribute-type-updated="handleAttributeTypeUpdated"
                />
              </div>
              <div class="col text-start">
                <label class="form-label">
                  category <small class="text-muted">(auto-detected)</small>
                </label>
                <AttributeCategorySelect
                  name="attribute.category"
                  :key="attribute.type"
                  :selected="attribute.category"
                  @attribute-category-updated="handleAttributeCategoryUpdated"
                />
              </div>
            </div>
            <div class="row m-2">
              <div class="col col-6 text-start">
                <label for="attribute.distribution" class="form-label"
                  >distribution</label
                >
                <DistributionLevelSelect
                  name="attribute.distribution"
                  :selected="attribute.distribution"
                  @distribution-level-updated="handleDistributionLevelUpdated"
                  :errors="errors['attribute.distribution']"
                />
                <div class="invalid-feedback">
                  {{ errors["attribute.distribution"] }}
                </div>
              </div>
            </div>
            <!-- TODO: sharing groups -->
            <!-- <div class="row m-2"> -->
            <!-- <div class="col col-6 text-start">
                  <label for="attributeSharingGroupId" class="form-label">Sharing Group</label>
                  <SharingGroupSelect v-model=attribute.sharing_group_id />
                  <div class="invalid-feedback">{{ errors[attribute.sharing_group_id'] }}</div>
                </div>
              </div> -->
            <div class="row m-2">
              <div class="col text-start">
                <label for="attribute.comment">comment</label>
                <Field
                  class="form-control"
                  id="attribute.comment"
                  name="attribute.comment"
                  as="textarea"
                  v-model="attribute.comment"
                  style="height: 50px"
                  :class="{ 'is-invalid': errors['attribute.comment'] }"
                >
                </Field>
                <div class="invalid-feedback">
                  {{ errors["attribute.comment"] }}
                </div>
              </div>
            </div>
            <div class="row m-2">
              <div class="col text-start">
                <div class="form-check">
                  <Field
                    class="form-control"
                    id="attribute.to_ids"
                    name="attribute.to_ids"
                    :value="attribute.push"
                    v-model="attribute.to_ids"
                    :class="{ 'is-invalid': errors['attribute.to_ids'] }"
                  >
                    <input
                      class="form-check-input"
                      type="checkbox"
                      v-model="attribute.to_ids"
                    />
                  </Field>
                  <label for="attribute.to_ids"
                    >for intrusion detection system (IDS)</label
                  >
                </div>
              </div>
            </div>
            <div class="row m-2">
              <div class="col text-start">
                <div class="form-check">
                  <Field
                    class="form-control"
                    id="attribute.disable_correlation"
                    name="attribute.disable_correlation"
                    :value="attribute.disable_correlation"
                    v-model="attribute.disable_correlation"
                    :class="{
                      'is-invalid': errors['attribute.disable_correlation'],
                    }"
                  >
                    <input
                      class="form-check-input"
                      type="checkbox"
                      v-model="attribute.disable_correlation"
                    />
                  </Field>
                  <label for="attribute.disable_correlation"
                    >disable correlation</label
                  >
                </div>
              </div>
            </div>
            <div class="row m-2">
              <div class="col col-6 text-start">
                <label for="attribute.first_seen">first seen</label>
                <Datepicker
                  v-model="attribute.first_seen"
                  name="attribute.first_seen"
                  altFormat="Z"
                  dateFormat="U"
                  enableTime
                />
              </div>
              <div class="col col-6 text-start">
                <label for="attribute.last_seen">last seen</label>
                <Datepicker
                  v-model="attribute.last_seen"
                  name="attribute.last_seen"
                  altFormat="Z"
                  dateFormat="U"
                  enableTime
                />
              </div>
            </div>
          </div>
          <div v-if="apiError" class="w-100 alert alert-danger mt-3 mb-3">
            <ApiError :errors="apiError" />
          </div>
          <div class="modal-footer">
            <button
              id="closeModalButton"
              type="button"
              data-bs-dismiss="modal"
              class="btn btn-secondary"
              @click="onClose()"
            >
              Discard
            </button>
            <button
              type="submit"
              class="btn btn-outline-primary"
              :disabled="status.loading"
            >
              <span v-show="status.loading">
                <span
                  class="spinner-border spinner-border-sm"
                  role="status"
                  aria-hidden="true"
                ></span>
              </span>
              <span v-show="!status.loading">Add</span>
            </button>
          </div>
        </div>
      </Form>
    </div>
  </div>
</template>
