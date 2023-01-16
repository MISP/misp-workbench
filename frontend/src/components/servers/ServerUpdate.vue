<script setup>
import { Form, Field } from "vee-validate";
import { storeToRefs } from 'pinia'
import { useServersStore } from "@/stores";
import { router } from "@/router";
import { ServerSchema } from "@/schemas/server";

const serversStore = useServersStore();
const { server, status, error } = storeToRefs(serversStore);

function onSubmit(values, { setErrors }) {
    return serversStore
        .update(values.server)
        .then((response) => {
            router.push(`/servers/${values.server.id}`);
        })
        .catch((error) => setErrors({ apiError: error }));
}

</script>

<template>
    <div class="card">
        <div class="card-header border-bottom">
            <div class="row">
                <div class="col-10">
                    <h3>Update Server</h3>
                </div>
            </div>
        </div>
        <div class="card-body d-flex flex-column">
            <Form @submit="onSubmit" :validation-schema="ServerSchema" v-slot="{ errors, isSubmitting }">
                <div class="mb-3">
                    <label for="server.id">id</label>
                    <Field class="form-control" id="server.id" name="server.id" v-model="server.id"
                        :class="{ 'is-invalid': errors['server.id'] }" disabled>
                    </Field>
                    <div class=" invalid-feedback">{{ errors['server.id'] }}</div>
                </div>
                <div class="mb-3">
                    <label for="server.name">name</label>
                    <Field class="form-control" id="server.name" name="server.name" v-model="server.name"
                        :class="{ 'is-invalid': errors['server.name'] }">
                    </Field>
                    <div class=" invalid-feedback">{{ errors['server.name'] }}</div>
                </div>
                <div class="mb-3">
                    <label for="server.url">url</label>
                    <Field class="form-control" id="server.url" name="server.url" v-model="server.url"
                        :class="{ 'is-invalid': errors['server.url'] }">
                    </Field>
                    <div class=" invalid-feedback">{{ errors['server.url'] }}</div>
                </div>
                <div class="mb-3">
                    <label for="server.authkey">authkey</label>
                    <Field class="form-control" id="server.authkey" name="server.authkey" v-model="server.authkey"
                        :class="{ 'is-invalid': errors['server.authkey'] }">
                    </Field>
                    <div class=" invalid-feedback">{{ errors['server.authkey'] }}</div>
                </div>
                <div class="mb-3">
                    <label for="server.org_id">organisation</label>
                    <Field class="form-control" id="server.org_id" name="server.org_id" v-model="server.org_id"
                        :class="{ 'is-invalid': errors['server.org_id'] }">
                    </Field>
                    <div class=" invalid-feedback">{{ errors['server.org_id'] }}</div>
                </div>
                <div class="mb-3">
                    <label for="server.push">push</label>
                    <Field class="form-control" id="server.push" name="server.push" :value="server.push"
                        v-model="server.push" :class="{ 'is-invalid': errors['server.push'] }">
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" v-model="server.push">
                        </div>
                    </Field>
                    <div class=" invalid-feedback">{{ errors['server.push'] }}</div>
                </div>
                <div class="mb-3">
                    <label for="server.pull">pull</label>
                    <Field class="form-control" id="server.pull" name="server.pull" :value="server.pull"
                        v-model="server.pull" :class="{ 'is-invalid': errors['server.pull'] }">
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" v-model="server.pull">
                        </div>
                    </Field>
                    <div class=" invalid-feedback">{{ errors['server.pull'] }}</div>
                </div>
                <div class="mb-3">
                    <label for="server.push_sightings">push_sightings</label>
                    <Field class="form-control" id="server.push_sightings" name="server.push_sightings"
                        :value="server.push_sightings" v-model="server.push_sightings"
                        :class="{ 'is-invalid': errors['server.push_sightings'] }">
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" v-model="server.push_sightings">
                        </div>
                    </Field>
                    <div class=" invalid-feedback">{{ errors['server.push_sightings'] }}</div>
                </div>
                <div class="mb-3">
                    <label for="server.push_galaxy_clusters">push_galaxy_clusters</label>
                    <Field class="form-control" id="server.push_galaxy_clusters" name="server.push_galaxy_clusters"
                        :value="server.push_galaxy_clusters" v-model="server.push_galaxy_clusters"
                        :class="{ 'is-invalid': errors['server.push_galaxy_clusters'] }">
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" v-model="server.push_galaxy_clusters">
                        </div>
                    </Field>
                    <div class=" invalid-feedback">{{ errors['server.push_galaxy_clusters'] }}</div>
                </div>
                <div class="mb-3">
                    <label for="server.pull_galaxy_clusters">pull_galaxy_clusters</label>
                    <Field class="form-control" id="server.pull_galaxy_clusters" name="server.pull_galaxy_clusters"
                        :value="server.pull_galaxy_clusters" v-model="server.pull_galaxy_clusters"
                        :class="{ 'is-invalid': errors['server.pull_galaxy_clusters'] }">
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" v-model="server.pull_galaxy_clusters">
                        </div>
                    </Field>
                    <div class=" invalid-feedback">{{ errors['server.pull_galaxy_clusters'] }}</div>
                </div>
                <div class="mb-3">
                    <label for="server.remote_org_id">remote organisation</label>
                    <Field class="form-control" id="server.remote_org_id" name="server.remote_org_id"
                        v-model="server.remote_org_id" :class="{ 'is-invalid': errors['server.remote_org_id'] }">
                    </Field>
                    <div class=" invalid-feedback">{{ errors['server.remote_org_id'] }}</div>
                </div>
                <div class="mb-3">
                    <label for="server.publish_without_email">publish_without_email</label>
                    <Field class="form-control" id="server.publish_without_email" name="server.publish_without_email"
                        :value="server.publish_without_email" v-model="server.publish_without_email"
                        :class="{ 'is-invalid': errors['server.publish_without_email'] }">
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" v-model="server.publish_without_email">
                        </div>
                    </Field>
                    <div class=" invalid-feedback">{{ errors['server.publish_without_email'] }}</div>
                </div>
                <div class="mb-3">
                    <label for="server.unpublish_event">unpublish_event</label>
                    <Field class="form-control" id="server.unpublish_event" name="server.unpublish_event"
                        :value="server.unpublish_event" v-model="server.unpublish_event"
                        :class="{ 'is-invalid': errors['server.unpublish_event'] }">
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" v-model="server.unpublish_event">
                        </div>
                    </Field>
                    <div class=" invalid-feedback">{{ errors['server.unpublish_event'] }}</div>
                </div>
                <div class="mb-3">
                    <label for="server.self_signed">self_signed</label>
                    <Field class="form-control" id="server.self_signed" name="server.self_signed"
                        :value="server.self_signed" v-model="server.self_signed"
                        :class="{ 'is-invalid': errors['server.self_signed'] }">
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" v-model="server.self_signed">
                        </div>
                    </Field>
                    <div class=" invalid-feedback">{{ errors['server.self_signed'] }}</div>
                </div>
                <div class="mb-3">
                    <label for="server.internal">internal</label>
                    <Field class="form-control" id="server.internal" name="server.internal" :value="server.internal"
                        v-model="server.internal" :class="{ 'is-invalid': errors['server.internal'] }">
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" v-model="server.internal">
                        </div>
                    </Field>
                    <div class=" invalid-feedback">{{ errors['server.internal'] }}</div>
                </div>
                <div class="mb-3">
                    <label for="server.skip_proxy">skip_proxy</label>
                    <Field class="form-control" id="server.skip_proxy" name="server.skip_proxy"
                        :value="server.skip_proxy" v-model="server.skip_proxy"
                        :class="{ 'is-invalid': errors['server.skip_proxy'] }">
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" v-model="server.skip_proxy">
                        </div>
                    </Field>
                    <div class=" invalid-feedback">{{ errors['server.skip_proxy'] }}</div>
                </div>
                <div class="mb-3">
                    <label for="server.caching_enabled">caching_enabled</label>
                    <Field class="form-control" id="server.caching_enabled" name="server.caching_enabled"
                        :value="server.caching_enabled" v-model="server.caching_enabled"
                        :class="{ 'is-invalid': errors['server.caching_enabled'] }">
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" v-model="server.caching_enabled">
                        </div>
                    </Field>
                    <div class=" invalid-feedback">{{ errors['server.caching_enabled'] }}</div>
                </div>
                <div class="mb-3">
                    <label for="server.priority">priority</label>
                    <Field class="form-control" id="server.priority" name="server.priority" v-model="server.priority"
                        :class="{ 'is-invalid': errors['server.priority'] }">
                    </Field>
                    <div class=" invalid-feedback">{{ errors['server.priority'] }}</div>
                </div>
                <div v-if="errors.apiError" class="w-100 alert alert-danger mt-3 mb-3">
                    {{ errors.apiError }}
                </div>
                <button type="submit" class="btn btn-primary" :class="{ 'disabled': status.updating }">
                    <span v-if="status.updating">
                        <span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
                    </span>
                    <span v-if="!status.updating">Save</span>
                </button>
            </Form>
        </div>
    </div>
</template>