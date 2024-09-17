<script setup>
import { Form, Field } from "vee-validate";
import { storeToRefs } from 'pinia';
import { useObjectsStore } from "@/stores";
import { router } from "@/router";
import { ObjectSchema } from "@/schemas/object";
import DistributionLevelSelect from "@/components/enums/DistributionLevelSelect.vue";

const objectsStore = useObjectsStore();
const { object, status, error } = storeToRefs(objectsStore);

function onSubmit(values, { setErrors }) {
    return objectsStore
        .update(values.object)
        .then((response) => {
            router.push(`/objects/${values.object.id}`);
        })
        .catch((error) => setErrors({ apiError: error }));
}

function handleDistributionLevelUpdated(distributionLevelId) {
    object.value.distribution = parseInt(distributionLevelId);
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
            <Form @submit="onSubmit" :validation-schema="ObjectSchema" v-slot="{ errors, isSubmitting }">
                <div class="mb-3">
                    <label for="object.id">id</label>
                    <Field class="form-control" id="object.id" name="object.id" v-model="object.id"
                        :class="{ 'is-invalid': errors['object.id'] }" disabled>
                    </Field>
                    <div class=" invalid-feedback">{{ errors['object.id'] }}</div>
                </div>
                <div class="mb-3">
                    <label for="object.uuid">uuid</label>
                    <Field class="form-control" id="object.uuid" name="object.uuid" v-model="object.uuid"
                        :class="{ 'is-invalid': errors['object.uuid'] }" disabled>
                    </Field>
                    <div class=" invalid-feedback">{{ errors['object.uuid'] }}</div>
                </div>
                <div class="mb-3">
                    <label for="object.timestamp">timestamp</label>
                    <Field class="form-control" id="object.timestamp" name="object.timestamp" v-model="object.timestamp"
                        :class="{ 'is-invalid': errors['object.timestamp'] }">
                    </Field>
                    <div class=" invalid-feedback">{{ errors['object.timestamp'] }}</div>
                </div>
                <div class="mb-3">
                    <label for="object.distribution" class="form-label">distribution</label>
                    <DistributionLevelSelect name="object.distribution" :selected=object.distribution
                        @distribution-level-updated="handleDistributionLevelUpdated"
                        :errors="errors['object.distribution']" />
                    <div class="invalid-feedback">{{ errors['object.distribution'] }}</div>
                </div>
                <div class="mb-3">
                    <label for="object.disable_correlation">disable correlation</label>
                    <Field class="form-control" id="object.disable_correlation" name="object.disable_correlation"
                        :value="object.push" v-model="object.disable_correlation"
                        :class="{ 'is-invalid': errors['object.disable_correlation'] }">
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" v-model="object.disable_correlation">
                        </div>
                    </Field>
                    <div class=" invalid-feedback">{{ errors['object.disable_correlation'] }}</div>
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