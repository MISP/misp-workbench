<script setup>
import { Form, Field } from "vee-validate";
import { storeToRefs } from 'pinia';
import { useAttributesStore } from "@/stores";
import { router } from "@/router";
import { AttributeSchema } from "@/schemas/attribute";
import DistributionLevelSelect from "@/components/enums/DistributionLevelSelect.vue";
import AnalysisLevelSelect from "@/components/enums/AnalysisLevelSelect.vue";
// import AttributeCategorySelect from "@/components/enums/AttributeCategorySelect.vue";
import AttributeTypeSelect from "@/components/enums/AttributeTypeSelect.vue";

const attributesStore = useAttributesStore();
const { attribute, status, error } = storeToRefs(attributesStore);

function onSubmit(values, { setErrors }) {
    return attributesStore
        .update(values.attribute)
        .then((response) => {
            router.push(`/attributes/${values.attribute.id}`);
        })
        .catch((error) => setErrors({ apiError: error }));
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
    <div class="card">
        <div class="card-header border-bottom">
            <div class="row">
                <div class="col-10">
                    <h3>Update Attribute</h3>
                </div>
            </div>
        </div>
        <div class="card-body d-flex flex-column">
            <Form @submit="onSubmit" :validation-schema="AttributeSchema" v-slot="{ errors, isSubmitting }">
                <div class="mb-3">
                    <label for="attribute.id">id</label>
                    <Field class="form-control" id="attribute.id" name="attribute.id" v-model="attribute.id"
                        :class="{ 'is-invalid': errors['attribute.id'] }" disabled>
                    </Field>
                    <div class=" invalid-feedback">{{ errors['attribute.id'] }}</div>
                </div>
                <div class="mb-3">
                    <label for="attribute.uuid">uuid</label>
                    <Field class="form-control" id="attribute.uuid" name="attribute.uuid" v-model="attribute.uuid"
                        :class="{ 'is-invalid': errors['attribute.uuid'] }" disabled>
                    </Field>
                    <div class=" invalid-feedback">{{ errors['attribute.uuid'] }}</div>
                </div>
                <div class="mb-3">
                    <label for="attribute.timestamp">timestamp</label>
                    <Field class="form-control" id="attribute.timestamp" name="attribute.timestamp"
                        v-model="attribute.timestamp" :class="{ 'is-invalid': errors['attribute.timestamp'] }">
                    </Field>
                    <div class=" invalid-feedback">{{ errors['attribute.timestamp'] }}</div>
                </div>
                <div class="mb-3">
                    <label for="attribute.distribution" class="form-label">distribution</label>
                    <DistributionLevelSelect name="attribute.distribution" :selected=attribute.distribution
                        @distribution-level-updated="handleDistributionLevelUpdated"
                        :errors="errors['attribute.distribution']" />
                    <div class="invalid-feedback">{{ errors['attribute.distribution'] }}</div>
                </div>
                <div class="mb-3">
                    <label for="attribute.disable_correlation">disable correlation</label>
                    <Field class="form-control" id="attribute.disable_correlation" name="attribute.disable_correlation"
                        :value="attribute.push" v-model="attribute.disable_correlation"
                        :class="{ 'is-invalid': errors['attribute.disable_correlation'] }">
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" v-model="attribute.disable_correlation">
                        </div>
                    </Field>
                    <div class=" invalid-feedback">{{ errors['attribute.disable_correlation'] }}</div>
                </div>
                <!-- <div class="mb-3">
                    <label for="attribute.category" class="form-label">category</label>
                    <AttributeCategorySelect name="attribute.category" :selected=attribute.category
                        @attribute-category-updated="handleAttributeCategoryUpdated"
                        :errors="errors['attribute.category']" />
                    <div class="invalid-feedback">{{ errors['attribute.category'] }}</div>
                </div> -->
                <div class="mb-3">
                    <label for="attribute.type" class="form-label">type</label>
                    <AttributeTypeSelect name="attribute.type" :category="attribute.category" :selected=attribute.type
                        @attribute-type-updated="handleAttributeTypeUpdated" :errors="errors['attribute.type']" />
                    <div class="invalid-feedback">{{ errors['attribute.type'] }}</div>
                </div>
                <div class="mb-3">
                    <label for="attribute.value">value</label>
                    <Field class="form-control" id="attribute.value" name="attribute.value" v-model="attribute.value"
                        :class="{ 'is-invalid': errors['attribute.value'] }">
                    </Field>
                    <div class=" invalid-feedback">{{ errors['attribute.value'] }}</div>
                </div>
                <div v-if="errors.apiError" class="w-100 alert alert-danger mt-3 mb-3">
                    {{ errors.apiError }}
                </div>
                <button type="submit" class="btn btn-outline-primary" :class="{ 'disabled': status.updating }">
                    <span v-if="status.updating">
                        <span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
                    </span>
                    <span v-if="!status.updating">Save</span>
                </button>
            </Form>
        </div>
    </div>
</template>