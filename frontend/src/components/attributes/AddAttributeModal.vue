<script setup>

import { ref } from 'vue';
import { useAttributesStore } from "@/stores";
import { storeToRefs } from 'pinia'
import { AttributeSchema } from "@/schemas/attribute";
import { DISTRIBUTION_LEVEL } from "@/helpers/constants";
import DistributionLevelSelect from "@/components/enums/DistributionLevelSelect.vue";
import AnalysisLevelSelect from "@/components/enums/AnalysisLevelSelect.vue";
import AttributeCategorySelect from "@/components/enums/AttributeCategorySelect.vue";
import AttributeTypeSelect from "@/components/enums/AttributeTypeSelect.vue";
import { Form, Field } from "vee-validate";
import * as Yup from "yup";

const attributesStore = useAttributesStore();
const { status } = storeToRefs(attributesStore);

const props = defineProps(['event_id']);
const emit = defineEmits(['attribute-created']);

const attribute = ref({
  distribution: DISTRIBUTION_LEVEL.INHERIT_EVENT,
  event_id: props.event_id,
  category: "Network activity",
  type: "ip-src",
  disable_correlation: false
});

function onSubmit(values, { setErrors }) {
  return attributesStore
    .create(attribute.value)
    .then((response) => {
      emit('attribute-created', { "attribute": response });
      document.getElementById('closeModalButton').click();
    })
    .catch((error) => setErrors({ apiError: error }));
}

function onClose() {
  attribute.value = {
    distribution: DISTRIBUTION_LEVEL.INHERIT_EVENT,
    event_id: props.event_id,
    category: "Network activity",
    type: "ip-src",
    disable_correlation: false
  };
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
</script>

<template>
  <div id="addAttributeModal" class="modal fade" tabindex="-1" aria-labelledby="addAttributeModalLabel"
    aria-hidden="true">
    <Form @submit="onSubmit" :validation-schema="AttributeSchema" v-slot="{ errors, isSubmitting }">
      <div class="modal-dialog modal-lg">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title" id="addAttributeModalLabel">Add Attribute</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Discard"></button>
          </div>
          <div class="modal-body">
            <div class="row m-2">
              <div class="col text-start">
                <label for="attribute.category" class="form-label">category</label>
                <AttributeCategorySelect name="attribute.category" :selected=attribute.category
                  @attribute-category-updated="handleAttributeCategoryUpdated" :errors="errors['attribute.category']" />
                <div class="invalid-feedback">{{ errors['attribute.category'] }}</div>
              </div>
              <div class="col text-start">
                <label for="attribute.type" class="form-label">type</label>
                <AttributeTypeSelect name="attribute.type" :category="attribute.category" :selected=attribute.type
                  @attribute-type-updated="handleAttributeTypeUpdated" :errors="errors['attribute.type']" />
                <div class="invalid-feedback">{{ errors['attribute.type'] }}</div>
              </div>
            </div>
            <div class="row m-2">
              <div class="col col-6 text-start">
                <label for="attribute.distribution" class="form-label">distribution</label>
                <DistributionLevelSelect name="attribute.distribution" :selected=attribute.distribution
                  @distribution-level-updated="handleDistributionLevelUpdated"
                  :errors="errors['attribute.distribution']" />
                <div class="invalid-feedback">{{ errors['attribute.distribution'] }}</div>
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
                <label for="attribute.value">value</label>
                <Field class="form-control" id="attribute.value" name="attribute.value" as="textarea"
                  v-model="attribute.value" style="height: 100px" :class="{ 'is-invalid': errors['attribute.value'] }">
                </Field>
                <div class=" invalid-feedback">{{ errors['attribute.value'] }}
                </div>
              </div>
            </div>
            <div class="row m-2">
              <div class="col text-start">
                <label for="attribute.comment">comment</label>
                <Field class="form-control" id="attribute.comment" name="attribute.comment" as="textarea"
                  v-model="attribute.comment" style="height: 100px"
                  :class="{ 'is-invalid': errors['attribute.comment'] }">
                </Field>
                <div class=" invalid-feedback">{{ errors['attribute.comment'] }}
                </div>
              </div>
            </div>
            <div class="row m-2">
              <div class="col text-start">
                <div class="form-check">
                  <Field class="form-control" id="attribute.to_ids" name="attribute.to_ids" :value="attribute.push"
                    v-model="attribute.to_ids" :class="{ 'is-invalid': errors['attribute.to_ids'] }">
                    <input class="form-check-input" type="checkbox" v-model="attribute.to_ids">
                  </Field>
                  <label for="attribute.to_ids">for intrusion detection system (IDS)</label>
                </div>
              </div>
            </div>
            <div class="row m-2">
              <div class="col text-start">
                <div class="form-check">
                  <Field class="form-control" id="attribute.batch_import" name="attribute.batch_import"
                    :value="attribute.push" v-model="attribute.batch_import"
                    :class="{ 'is-invalid': errors['attribute.batch_import'] }">
                    <input class="form-check-input" type="checkbox" v-model="attribute.batch_import">
                  </Field>
                  <label for="attribute.batch_import">batch import</label>
                </div>
              </div>
            </div>
            <div class="row m-2">
              <div class="col text-start">
                <div class="form-check">
                  <Field class="form-control" id="attribute.disable_correlation" name="attribute.disable_correlation"
                    :value="attribute.push" v-model="attribute.disable_correlation"
                    :class="{ 'is-invalid': errors['attribute.disable_correlation'] }">
                    <input class="form-check-input" type="checkbox" v-model="attribute.disable_correlation">
                  </Field>
                  <label for="attribute.disable_correlation">disable correlation</label>
                </div>
              </div>
            </div>
            <div class="row m-2">
              <div class="col col-6 text-start">
                <label for="attribute.value">first seen</label>
                <Field class="form-control" id="attribute.first_seen" name="attribute.first_seen"
                  placeholder="DD/MM/YYYY HH:MM:SS.ssssss+TT:TT" v-model="attribute.first_seen"
                  :class="{ 'is-invalid': errors['attribute.first_seen'] }">
                </Field>
                <div class=" invalid-feedback">{{ errors['attribute.first_seen'] }}
                </div>
              </div>
              <div class="col col-6 text-start">
                <label for="attribute.value">first seen</label>
                <Field class="form-control" id="attribute.last_seen" name="attribute.last_seen"
                  placeholder="DD/MM/YYYY HH:MM:SS.ssssss+TT:TT" v-model="attribute.last_seen"
                  :class="{ 'is-invalid': errors['attribute.last_seen'] }">
                </Field>
                <div class=" invalid-feedback">{{ errors['attribute.last_seen'] }}
                </div>
              </div>
            </div>
          </div>
          <div v-if="errors.apiError" class="w-100 alert alert-danger mt-3 mb-3">
            {{ errors.apiError }}
          </div>
          <div class="modal-footer">
            <button id="closeModalButton" type="button" data-bs-dismiss="modal" class="btn btn-secondary"
              @click="onClose()">Discard</button>
            <button type="submit" class="btn btn-outline-primary" :disabled="status.loading">
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
