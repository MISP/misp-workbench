<script setup>
import { ref, watch } from "vue";
import { Form, Field } from "vee-validate";
import { storeToRefs } from "pinia";
import { useServersStore } from "@/stores";
import { router } from "@/router";
import { ServerSchema } from "@/schemas/server";
import OrganisationsSelect from "@/components/organisations/OrganisationsSelect.vue";
import PullRulesEditor from "@/components/servers/PullRulesEditor.vue";

const serversStore = useServersStore();
const { status } = storeToRefs(serversStore);

const server = {
  push: false,
  pull: false,
  pull_rules: {},
  push_galaxy_clusters: false,
  pull_galaxy_clusters: false,
  push_sightings: false,
  publish_without_email: false,
  unpublish_event: false,
  self_signed: false,
  internal: false,
  skip_proxy: false,
  caching_enabled: false,
  priority: 0,
};

const pullRules = ref(JSON.stringify(server.pull_rules, null, 2));
watch(pullRules, (newVal) => {
  try {
    const rules = JSON.parse(newVal);
    server.pull_rules = rules;
  } catch {}
});

function onSubmit(values, { setErrors }) {
  return serversStore
    .create(server)
    .then((response) => {
      router.push(`/servers/${response.id}`);
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

<style>
.editor-container .cm-editor {
  height: 200px;
  width: 600px;
  border: 1px solid #ccc;
  border-radius: 6px;
  font-family: monospace;
}
</style>

<template>
  <div class="card">
    <div class="card-header border-bottom">
      <div class="row">
        <div class="col-10">
          <h3>Add Server</h3>
          {{ server.role_id }}
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
        <div class="mb-3">
          <label for="server.push">push</label>
          <Field
            class="form-control"
            id="server.push"
            name="server.push"
            :value="server.push"
            v-model="server.push"
            :class="{ 'is-invalid': errors['server.push'] }"
          >
            <div class="form-check">
              <input
                class="form-check-input"
                type="checkbox"
                v-model="server.push"
              />
            </div>
          </Field>
          <div class="invalid-feedback">{{ errors["server.push"] }}</div>
        </div>
        <div class="mb-3">
          <label for="server.pull">pull</label>
          <Field
            class="form-control"
            id="server.pull"
            name="server.pull"
            :value="server.pull"
            v-model="server.pull"
            :class="{ 'is-invalid': errors['server.pull'] }"
          >
            <div class="form-check">
              <input
                class="form-check-input"
                type="checkbox"
                v-model="server.pull"
              />
            </div>
          </Field>
          <div class="invalid-feedback">{{ errors["server.pull"] }}</div>
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
        <p>
          <a
            class="btn-primary"
            data-bs-toggle="collapse"
            href="#advancedSettings"
            role="button"
            aria-expanded="false"
            aria-controls="advancedSettings"
          >
            Advanced Options <font-awesome-icon icon="fa-solid fa-caret-down" />
          </a>
        </p>
        <div class="collapse" id="advancedSettings">
          <div class="mb-3">
            <label for="server.push_sightings">push_sightings</label>
            <Field
              class="form-control"
              id="server.push_sightings"
              name="server.push_sightings"
              :value="server.push_sightings"
              v-model="server.push_sightings"
              :class="{ 'is-invalid': errors['server.push_sightings'] }"
            >
              <div class="form-check">
                <input
                  class="form-check-input"
                  type="checkbox"
                  v-model="server.push_sightings"
                />
              </div>
            </Field>
            <div class="invalid-feedback">
              {{ errors["server.push_sightings"] }}
            </div>
          </div>
          <div class="mb-3">
            <label for="server.push_galaxy_clusters"
              >push_galaxy_clusters</label
            >
            <Field
              class="form-control"
              id="server.push_galaxy_clusters"
              name="server.push_galaxy_clusters"
              :value="server.push_galaxy_clusters"
              v-model="server.push_galaxy_clusters"
              :class="{ 'is-invalid': errors['server.push_galaxy_clusters'] }"
            >
              <div class="form-check">
                <input
                  class="form-check-input"
                  type="checkbox"
                  v-model="server.push_galaxy_clusters"
                />
              </div>
            </Field>
            <div class="invalid-feedback">
              {{ errors["server.push_galaxy_clusters"] }}
            </div>
          </div>
          <div class="mb-3">
            <label for="server.pull_galaxy_clusters"
              >pull_galaxy_clusters</label
            >
            <Field
              class="form-control"
              id="server.pull_galaxy_clusters"
              name="server.pull_galaxy_clusters"
              :value="server.pull_galaxy_clusters"
              v-model="server.pull_galaxy_clusters"
              :class="{ 'is-invalid': errors['server.pull_galaxy_clusters'] }"
            >
              <div class="form-check">
                <input
                  class="form-check-input"
                  type="checkbox"
                  v-model="server.pull_galaxy_clusters"
                />
              </div>
            </Field>
            <div class="invalid-feedback">
              {{ errors["server.pull_galaxy_clusters"] }}
            </div>
          </div>
          <div class="mb-3">
            <label for="server.publish_without_email"
              >publish_without_email</label
            >
            <Field
              class="form-control"
              id="server.publish_without_email"
              name="server.publish_without_email"
              :value="server.publish_without_email"
              v-model="server.publish_without_email"
              :class="{ 'is-invalid': errors['server.publish_without_email'] }"
            >
              <div class="form-check">
                <input
                  class="form-check-input"
                  type="checkbox"
                  v-model="server.publish_without_email"
                />
              </div>
            </Field>
            <div class="invalid-feedback">
              {{ errors["server.publish_without_email"] }}
            </div>
          </div>
          <div class="mb-3">
            <label for="server.unpublish_event">unpublish_event</label>
            <Field
              class="form-control"
              id="server.unpublish_event"
              name="server.unpublish_event"
              :value="server.unpublish_event"
              v-model="server.unpublish_event"
              :class="{ 'is-invalid': errors['server.unpublish_event'] }"
            >
              <div class="form-check">
                <input
                  class="form-check-input"
                  type="checkbox"
                  v-model="server.unpublish_event"
                />
              </div>
            </Field>
            <div class="invalid-feedback">
              {{ errors["server.unpublish_event"] }}
            </div>
          </div>
          <div class="mb-3">
            <label for="server.self_signed">self_signed</label>
            <Field
              class="form-control"
              id="server.self_signed"
              name="server.self_signed"
              :value="server.self_signed"
              v-model="server.self_signed"
              :class="{ 'is-invalid': errors['server.self_signed'] }"
            >
              <div class="form-check">
                <input
                  class="form-check-input"
                  type="checkbox"
                  v-model="server.self_signed"
                />
              </div>
            </Field>
            <div class="invalid-feedback">
              {{ errors["server.self_signed"] }}
            </div>
          </div>
          <div class="mb-3">
            <label for="server.internal">internal</label>
            <Field
              class="form-control"
              id="server.internal"
              name="server.internal"
              :value="server.internal"
              v-model="server.internal"
              :class="{ 'is-invalid': errors['server.internal'] }"
            >
              <div class="form-check">
                <input
                  class="form-check-input"
                  type="checkbox"
                  v-model="server.internal"
                />
              </div>
            </Field>
            <div class="invalid-feedback">{{ errors["server.internal"] }}</div>
          </div>
          <div class="mb-3">
            <label for="server.skip_proxy">skip_proxy</label>
            <Field
              class="form-control"
              id="server.skip_proxy"
              name="server.skip_proxy"
              :value="server.skip_proxy"
              v-model="server.skip_proxy"
              :class="{ 'is-invalid': errors['server.skip_proxy'] }"
            >
              <div class="form-check">
                <input
                  class="form-check-input"
                  type="checkbox"
                  v-model="server.skip_proxy"
                />
              </div>
            </Field>
            <div class="invalid-feedback">
              {{ errors["server.skip_proxy"] }}
            </div>
          </div>
          <div class="mb-3">
            <label for="server.caching_enabled">caching_enabled</label>
            <Field
              class="form-control"
              id="server.caching_enabled"
              name="server.caching_enabled"
              :value="server.caching_enabled"
              v-model="server.caching_enabled"
              :class="{ 'is-invalid': errors['server.caching_enabled'] }"
            >
              <div class="form-check">
                <input
                  class="form-check-input"
                  type="checkbox"
                  v-model="server.caching_enabled"
                />
              </div>
            </Field>
            <div class="invalid-feedback">
              {{ errors["server.caching_enabled"] }}
            </div>
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
        </div>
        <div v-if="errors.apiError" class="w-100 alert alert-danger mt-3 mb-3">
          {{ errors.apiError }}
        </div>
        <button
          type="submit"
          class="btn btn-outline-primary"
          :class="{ disabled: status.creating }"
        >
          <span v-if="status.creating">
            <span
              class="spinner-border spinner-border-sm"
              role="status"
              aria-hidden="true"
            ></span>
          </span>
          <span v-if="!status.creating">Create</span>
        </button>
      </Form>
    </div>
  </div>
</template>
