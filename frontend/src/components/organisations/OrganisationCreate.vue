<script setup>
import { Form, Field } from "vee-validate";
import { storeToRefs } from 'pinia'
import { useOrganisationsStore } from "@/stores";
import { router } from "@/router";
import { OrganisationSchema } from "@/schemas/organisation";

const organisationsStore = useOrganisationsStore();
const { status, error } = storeToRefs(organisationsStore);

let organisation = {
    local: true,
};

function onSubmit(values, { setErrors }) {
    return organisationsStore
        .create(organisation)
        .then((response) => {
            router.push(`/organisations/${response.id}`);
        })
        .catch((error) => setErrors({ apiError: error }));
}
</script>

<template>
    <div class="card">
        <div class="card-header border-bottom">
            <div class="row">
                <div class="col-10">
                    <h3>Create Organisation</h3>
                </div>
            </div>
        </div>
        <div class="card-body d-flex flex-column">
            <Form @submit="onSubmit" :validation-schema="OrganisationSchema" v-slot="{ errors, isSubmitting }">
                <div class="mb-3">
                    <label for="organisation.uuid">uuid</label>
                    <Field class="form-control" id="organisation.uuid" name="organisation.uuid" v-model="organisation.uuid"
                        :class="{ 'is-invalid': errors['organisation.uuid'] }">
                    </Field>
                    <div class=" invalid-feedback">{{ errors['organisation.uuid'] }}</div>
                </div>
                <div class="mb-3">
                    <label for="organisation.name">name</label>
                    <Field class="form-control" id="organisation.name" name="organisation.name"
                        v-model="organisation.name" :class="{ 'is-invalid': errors['organisation.name'] }">
                    </Field>
                    <div class=" invalid-feedback">{{ errors['organisation.name'] }}</div>
                </div>
                <div class="mb-3">
                    <label for="organisation.description">description</label>
                    <Field class="form-control" id="organisation.description" name="organisation.description"
                        v-model="organisation.description"
                        :class="{ 'is-invalid': errors['organisation.description'] }">
                    </Field>
                    <div class=" invalid-feedback">{{ errors['organisation.description'] }}</div>
                </div>
                <div class="mb-3">
                    <label for="organisation.type">type</label>
                    <Field class="form-control" id="organisation.type" name="organisation.type"
                        v-model="organisation.type" :class="{ 'is-invalid': errors['organisation.type'] }">
                    </Field>
                    <div class=" invalid-feedback">{{ errors['organisation.type'] }}</div>
                </div>
                <div class="mb-3">
                    <label for="organisation.local">local</label>
                    <Field class="form-control" id="organisation.local" name="organisation.local"
                        :value="organisation.local" v-model="organisation.local"
                        :class="{ 'is-invalid': errors['organisation.local'] }">
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" v-model="organisation.local">
                        </div>
                    </Field>
                    <div class=" invalid-feedback">{{ errors['organisation.local'] }}</div>
                </div>
                <div class="mb-3">
                    <label for="organisation.nationality">nationality</label>
                    <Field class="form-control" id="organisation.nationality" name="organisation.nationality"
                        v-model="organisation.nationality"
                        :class="{ 'is-invalid': errors['organisation.nationality'] }">
                    </Field>
                    <div class=" invalid-feedback">{{ errors['organisation.nationality'] }}</div>
                </div>
                <div class="mb-3">
                    <label for="organisation.sector">sector</label>
                    <Field class="form-control" id="organisation.sector" name="organisation.sector"
                        v-model="organisation.sector"
                        :class="{ 'is-invalid': errors['organisation.sector'] }">
                    </Field>
                    <div class=" invalid-feedback">{{ errors['organisation.sector'] }}</div>
                </div>
                <div class="mb-3">
                    <label for="organisation.restricted_to_domain">restricted_to_domain</label>
                    <Field class="form-control" id="organisation.restricted_to_domain" name="organisation.restricted_to_domain"
                        v-model="organisation.restricted_to_domain"
                        :class="{ 'is-invalid': errors['organisation.restricted_to_domain'] }">
                    </Field>
                    <div class=" invalid-feedback">{{ errors['organisation.restricted_to_domain'] }}</div>
                </div>
                <div v-if="errors.apiError" class="w-100 alert alert-danger mt-3 mb-3">
                    {{ errors.apiError }}
                </div>
                <button type="submit" class="btn btn-primary" :class="{ 'disabled': status.creating }">
                    <span v-if="status.creating">
                        <span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
                    </span>
                    <span v-if="!status.creating">Create</span>
                </button>
            </Form>
        </div>
    </div>
</template>