<script setup>

import { ref } from 'vue';
import { useAttributesStore } from "@/stores";
import { storeToRefs } from 'pinia'
import DistributionLevelSelect from "@/components/enums/DistributionLevelSelect.vue";
import { ATTRIBUTE_CATEGORIES, DISTRIBUTION_LEVEL } from "@/helpers/constants";
import { Form, Field } from "vee-validate";
import * as Yup from "yup";

const attributesStore = useAttributesStore();
const { status } = storeToRefs(attributesStore);

const props = defineProps(['event_id']);
const emit = defineEmits(['attribute-created']);

const attribute = ref({
  distribution: DISTRIBUTION_LEVEL.INHERIT_EVENT,
  event_id: props.event_id,
});

const schema = Yup.object().shape({
  attribute: Yup.object().shape({
    category: Yup.string().required("Category is required"),
    type: Yup.string().required("Type is required"),
    value: Yup.string().required("Value is required"),
  }),
});

function onSubmit(values, { setErrors }) {
  return attributesStore
    .create(attribute.value)
    .then((response) => {
      emit('attribute-created', { "attribute": response });
    })
    .catch((error) => setErrors({ apiError: error }));
}

function onClose() {
  attribute.value = {
    distribution: DISTRIBUTION_LEVEL.INHERIT_EVENT,
    event_id: props.event_id,
  };
}

function handleDistributionLevelUpdated(distributionLevelId) {
  attribute.value.distribution = distributionLevelId;
}
</script>

<template>
  <div id="addAttributeModal" class="modal fade" tabindex="-1" aria-labelledby="addAttributeModalLabel"
    aria-hidden="true">
    <Form @submit="onSubmit" :validation-schema="schema" v-slot="{ errors, isSubmitting }">
      <div class="modal-dialog modal-lg">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title" id="addAttributeModalLabel">Add Attribute</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Discard"></button>
          </div>
          <div class="modal-body">
            <div class="row m-2">
              <div class="col text-start">
                <label for="attribute.category" class="form-label">Category</label>
                <Field id="attribute.category" name="attribute.category" v-model="attribute.category" as="select"
                  class="form-control" :class="{ 'is-invalid': errors['attribute.category'] }">
                  <option selected disabled value="">Choose...</option>
                  <option v-for="(category, id) in ATTRIBUTE_CATEGORIES" :value="id">{{ id }}</option>
                </Field>
                <div class="invalid-feedback">{{ errors['attribute.category'] }}</div>
              </div>
              <div class="col text-start">
                <label for="attribute.type" class="form-label">Type</label>
                <Field id="attribute.type" name="attribute.type" v-model="attribute.type" as="select"
                  class="form-control" :class="{ 'is-invalid': errors['attribute.type'] }">
                  <option selected disabled value="">Choose...</option>
                  <option v-if="attribute.category"
                    v-for="attributeType in ATTRIBUTE_CATEGORIES[attribute.category].types" :value="attributeType">
                    {{ attributeType }}</option>
                </Field>
                <div class="invalid-feedback">{{ errors['attribute.type'] }}</div>
              </div>
            </div>
            <div class="row m-2">
              <div class="col col-6 text-start">
                <label for="attribute.distribution" class="form-label">Distribution</label>
                <DistributionLevelSelect name="attribute.distribution" :selected=attribute.distribution
                  @distribution-level-updated="handleDistributionLevelUpdated" />
                <div class="invalid-feedback">{{ errors['attribute.distribution'] }}</div>
              </div>
              <!-- TODO -->
              <!-- <div class="col col-6 text-start">
                <label for="attributeType" class="form-label">Sharing Group</label>
                <SharingGroupSelect v-model=attribute.sharing_group_id />
                <div class="invalid-feedback">{{ errors[attribute.sharing_group_id'] }}</div>
              </div> -->
            </div>
            <div class="row m-2">
              <div class="col text-start">
                <label for="attribute.value">Value</label>
                <Field class="form-control" id="attribute.value" name="attribute.value" as="textarea"
                  v-model="attribute.value" style="height: 100px" :class="{ 'is-invalid': errors['attribute.value'] }">
                </Field>
                <div class=" invalid-feedback">{{ errors['attribute.value'] }}
                </div>
              </div>
            </div>
            <div class="row m-2">
              <div class="col text-start">
                <label for="attributeComment">Comment</label>
                <input class="form-control" id="attributeComment" name="attributeComment" v-model="attribute.comment">
              </div>
            </div>
            <div class="row m-2">
              <div class="col text-start">
                <div class="form-check form-switch">
                  <input class="form-check-input" type="checkbox" value="" id="attributeIDS" name="attributeIDS">
                  <label class="form-check-label" for="attributeIDS">For Intrusion Detection System</label>
                </div>
              </div>
            </div>
            <div class="row m-2">
              <div class="col text-start">
                <div class="form-check">
                  <input class="form-check-input" type="checkbox" value="" id="attributeBatchImport"
                    name="attributeBatchImport">
                  <label class="form-check-label" for="attributeBatchImport">Batch Import</label>
                </div>
              </div>
            </div>
            <div class="row m-2">
              <div class="col text-start">
                <div class="form-check">
                  <input class="form-check-input" type="checkbox" value="" id="attributeDisableCorrelation"
                    name="attributeDisableCorrelation" v-model="attribute.disable_correlation">
                  <label class="form-check-label" for="attributeDisableCorrelation">Disable Correlation</label>
                </div>
              </div>
            </div>
            <div class="row m-2">
              <div class="col col-6 text-start">
                <label for="attributeFirstSeen">First seen</label>
                <input class="form-control" id="attributeFirstSeen" name="attributeFirstSeen"
                  v-model="attribute.first_seen" placeholder="DD/MM/YYYY HH:MM:SS.ssssss+TT:TT">
              </div>
              <div class="col col-6 text-start">
                <label for="attributeLastSeen">Last seen</label>
                <input class="form-control" id="attributeLastSeen" name="attributeLastSeen"
                  v-model="attribute.last_seen" placeholder="DD/MM/YYYY HH:MM:SS.ssssss+TT:TT">
              </div>
            </div>
          </div>
          <div v-if="errors.apiError" class="w-100 alert alert-danger mt-3 mb-3">
            {{ errors.apiError }}
          </div>
          <div class="modal-footer">
            <button type="button" data-bs-dismiss="modal" class="btn btn-secondary" @click="onClose()">Discard</button>
            <button type="submit" data-bs-dismiss="modal" class="btn btn-primary"
              :class="{ 'disabled': status.loading }">
              <span v-show="status.loading">
                <span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
              </span>
              <span v-show="!status.loading">Add</span>
            </button>
          </div>
        </div>
      </div>
    </Form>
  </div>
</template>
