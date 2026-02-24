<script setup>
import { computed } from "vue";
import { Form, Field } from "vee-validate";
import { storeToRefs } from "pinia";
import { useServersStore } from "@/stores";
import { router } from "@/router";
import { ServerSchema } from "@/schemas/server";
import OrganisationsSelect from "@/components/organisations/OrganisationsSelect.vue";
import PullRulesEditor from "@/components/servers/PullRulesEditor.vue";

const serversStore = useServersStore();
const { server, status } = storeToRefs(serversStore);

const pullRules = computed({
  get: () => server.value.pull_rules ?? {},
  set: (val) => {
    server.value.pull_rules = val;
  },
});

function onSubmit(values, { setErrors }) {
  return serversStore
    .update(values.server)
    .then(() => {
      router.push(`/servers/${values.server.id}`);
    })
    .catch((error) => setErrors({ apiError: error }));
}

function handleOrganisationUpdated(orgId) {
  server.org_id = orgId;
}
function handleRemoteOrgUpdated(orgId) {
  server.remote_org_id = orgId;
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
      <Form
        @submit="onSubmit"
        :validation-schema="ServerSchema"
        v-slot="{ errors }"
      >
        <div class="mb-3">
          <label for="server.id">id</label>
          <Field
            class="form-control"
            id="server.id"
            name="server.id"
            v-model="server.id"
            :class="{ 'is-invalid': errors['server.id'] }"
            disabled
          >
          </Field>
          <div class="invalid-feedback">{{ errors["server.id"] }}</div>
        </div>
        <div class="mb-3">
          <label for="server.name">name</label>
          <Field
            class="form-control"
            id="server.name"
            name="server.name"
            v-model="server.name"
            :class="{ 'is-invalid': errors['server.name'] }"
          >
          </Field>
          <div class="invalid-feedback">{{ errors["server.name"] }}</div>
        </div>
        <div class="mb-3">
          <label for="server.url">url</label>
          <Field
            class="form-control"
            id="server.url"
            name="server.url"
            v-model="server.url"
            :class="{ 'is-invalid': errors['server.url'] }"
          >
          </Field>
          <div class="invalid-feedback">{{ errors["server.url"] }}</div>
        </div>
        <div class="mb-3">
          <label for="server.authkey">authkey</label>
          <Field
            class="form-control"
            id="server.authkey"
            type="password"
            name="server.authkey"
            v-model="server.authkey"
            :class="{ 'is-invalid': errors['server.authkey'] }"
          >
          </Field>
          <div class="invalid-feedback">{{ errors["server.authkey"] }}</div>
        </div>
        <div class="mb-3">
          <label for="server.org_id">organisation</label>
          <OrganisationsSelect
            name="server.org_id"
            :selected="server.org_id"
            @organisation-updated="handleOrganisationUpdated"
            :errors="errors['server.org_id']"
          />
          <div class="invalid-feedback">{{ errors["server.org_id"] }}</div>
        </div>
        <div class="mb-3">
          <label for="server.remote_org_id">remote organisation</label>
          <OrganisationsSelect
            name="server.remote_org_id"
            :selected="server.remote_org_id"
            @organisation-updated="handleRemoteOrgUpdated"
            :errors="errors['server.remote_org_id']"
          />
          <div class="invalid-feedback">
            {{ errors["server.remote_org_id"] }}
          </div>
        </div>
        <div class="form-check form-switch mb-3">
          <input
            class="form-check-input"
            type="checkbox"
            role="switch"
            id="server.push"
            v-model="server.push"
          />
          <label class="form-check-label" for="server.push">Push</label>
        </div>
        <div class="form-check form-switch mb-3">
          <input
            class="form-check-input"
            type="checkbox"
            role="switch"
            id="server.pull"
            v-model="server.pull"
          />
          <label class="form-check-label" for="server.pull">Pull</label>
        </div>
        <div class="mb-3">
          <label for="server.pull_rules">pull_rules</label>
          <Field
            class="form-control"
            type="hidden"
            id="server.pull_rules"
            name="server.pull_rules"
            v-model="server.pull_rules"
          ></Field>
          <PullRulesEditor v-model="pullRules" />
          <div class="invalid-feedback">{{ errors["server.pull_rules"] }}</div>
        </div>
        <div class="form-check form-switch mb-3">
          <input
            class="form-check-input"
            type="checkbox"
            role="switch"
            id="server.push_sightings"
            v-model="server.push_sightings"
          />
          <label class="form-check-label" for="server.push_sightings"
            >Push Sightings</label
          >
        </div>
        <div class="form-check form-switch mb-3">
          <input
            class="form-check-input"
            type="checkbox"
            role="switch"
            id="server.push_galaxy_clusters"
            v-model="server.push_galaxy_clusters"
          />
          <label class="form-check-label" for="server.push_galaxy_clusters"
            >Push Galaxy Clusters</label
          >
        </div>
        <div class="form-check form-switch mb-3">
          <input
            class="form-check-input"
            type="checkbox"
            role="switch"
            id="server.pull_galaxy_clusters"
            v-model="server.pull_galaxy_clusters"
          />
          <label class="form-check-label" for="server.pull_galaxy_clusters"
            >Pull Galaxy Clusters</label
          >
        </div>
        <div class="form-check form-switch mb-3">
          <input
            class="form-check-input"
            type="checkbox"
            role="switch"
            id="server.publish_without_email"
            v-model="server.publish_without_email"
          />
          <label class="form-check-label" for="server.publish_without_email"
            >Publish Without Email</label
          >
        </div>
        <div class="form-check form-switch mb-3">
          <input
            class="form-check-input"
            type="checkbox"
            role="switch"
            id="server.unpublish_event"
            v-model="server.unpublish_event"
          />
          <label class="form-check-label" for="server.unpublish_event"
            >Unpublish Event</label
          >
        </div>
        <div class="form-check form-switch mb-3">
          <input
            class="form-check-input"
            type="checkbox"
            role="switch"
            id="server.self_signed"
            v-model="server.self_signed"
          />
          <label class="form-check-label" for="server.self_signed"
            >Self Signed</label
          >
        </div>
        <div class="form-check form-switch mb-3">
          <input
            class="form-check-input"
            type="checkbox"
            role="switch"
            id="server.internal"
            v-model="server.internal"
          />
          <label class="form-check-label" for="server.internal">Internal</label>
        </div>
        <div class="form-check form-switch mb-3">
          <input
            class="form-check-input"
            type="checkbox"
            role="switch"
            id="server.skip_proxy"
            v-model="server.skip_proxy"
          />
          <label class="form-check-label" for="server.skip_proxy"
            >Skip Proxy</label
          >
        </div>
        <div class="form-check form-switch mb-3">
          <input
            class="form-check-input"
            type="checkbox"
            role="switch"
            id="server.caching_enabled"
            v-model="server.caching_enabled"
          />
          <label class="form-check-label" for="server.caching_enabled"
            >Caching Enabled</label
          >
        </div>
        <div class="mb-3">
          <label for="server.priority">priority</label>
          <Field
            class="form-control"
            id="server.priority"
            name="server.priority"
            v-model="server.priority"
            :class="{ 'is-invalid': errors['server.priority'] }"
          >
          </Field>
          <div class="invalid-feedback">{{ errors["server.priority"] }}</div>
        </div>
        <div v-if="errors.apiError" class="w-100 alert alert-danger mt-3 mb-3">
          {{ errors.apiError }}
        </div>
        <button
          type="submit"
          class="btn btn-outline-primary"
          :class="{ disabled: status.updating }"
        >
          <span v-if="status.updating">
            <span
              class="spinner-border spinner-border-sm"
              role="status"
              aria-hidden="true"
            ></span>
          </span>
          <span v-if="!status.updating">Save</span>
        </button>
      </Form>
    </div>
  </div>
</template>
