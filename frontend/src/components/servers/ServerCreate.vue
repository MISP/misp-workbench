<script setup>
import { ref, computed, reactive } from "vue";
import { Form, Field } from "vee-validate";
import { storeToRefs } from "pinia";
import { useServersStore } from "@/stores";
import { router } from "@/router";
import { ServerSchema } from "@/schemas/server";
import OrganisationsSelect from "@/components/organisations/OrganisationsSelect.vue";
import PullRulesEditor from "@/components/servers/PullRulesEditor.vue";
import PreviewPullModal from "@/components/servers/PreviewPullModal.vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faLink } from "@fortawesome/free-solid-svg-icons";
const serversStore = useServersStore();
const { status } = storeToRefs(serversStore);

const server = reactive({
  push: false,
  pull: false,
  pull_rules: { timestamp: "30d" },
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
});

const previewResult = ref(null);
const previewError = ref(null);
const previewOpen = ref(false);

const canPreview = computed(() => !!server.url && !!server.authkey);

function onSubmit(_, { setErrors }) {
  return serversStore
    .create(server)
    .then((response) => {
      router.push(`/servers/${response.id}`);
    })
    .catch((error) => setErrors({ apiError: error }));
}

async function preview() {
  previewResult.value = null;
  previewError.value = null;
  try {
    previewResult.value = await serversStore.previewPull({
      url: server.url,
      authkey: server.authkey,
      self_signed: server.self_signed,
      pull_rules: server.pull_rules,
    });
    previewOpen.value = true;
  } catch (error) {
    previewError.value =
      typeof error === "string" ? error : "Failed to connect to remote server.";
  }
}

function handleOrganisationUpdated(orgId) {
  server.org_id = orgId;
}
function handleRemoteOrgUpdated(orgId) {
  server.remote_org_id = orgId;
}

function cancel() {
  router.push("/servers");
}
</script>

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
          <label for="server.name">Name</label>
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
          <label for="server.url">URL</label>
          <div class="input-group mb-3">
            <div class="input-group-prepend">
              <span class="input-group-text">
                <span>
                  <FontAwesomeIcon :icon="faLink" class="btg-lg" />
                </span>
              </span>
            </div>
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
        </div>
        <div class="mb-3">
          <label for="server.authkey">API authkey</label>
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
          <label for="server.org_id">Organisation</label>
          <OrganisationsSelect
            name="server.org_id"
            :selected="server.org_id"
            @organisation-updated="handleOrganisationUpdated"
            :errors="errors['server.org_id']"
          />
          <div class="invalid-feedback">{{ errors["server.org_id"] }}</div>
        </div>
        <div class="mb-3">
          <label for="server.remote_org_id">Remote Organisation</label>
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
          <Field
            class="form-control"
            type="hidden"
            id="server.pull_rules"
            name="server.pull_rules"
            v-model="server.pull_rules"
          ></Field>
          <PullRulesEditor v-model="server.pull_rules" />
          <div class="invalid-feedback">{{ errors["server.pull_rules"] }}</div>
        </div>
        <div class="card mb-3">
          <div class="card-header">
            <a
              class="text-decoration-none fw-semibold"
              data-bs-toggle="collapse"
              href="#advancedSettings"
              role="button"
              aria-expanded="false"
              aria-controls="advancedSettings"
            >
              Advanced Options
              <font-awesome-icon icon="fa-solid fa-caret-down" />
            </a>
          </div>
          <div class="collapse" id="advancedSettings">
            <div class="card-body">
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
                <label
                  class="form-check-label"
                  for="server.push_galaxy_clusters"
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
                <label
                  class="form-check-label"
                  for="server.pull_galaxy_clusters"
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
                <label
                  class="form-check-label"
                  for="server.publish_without_email"
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
                <label class="form-check-label" for="server.internal"
                  >Internal</label
                >
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
                <div class="invalid-feedback">
                  {{ errors["server.priority"] }}
                </div>
              </div>
            </div>
          </div>
        </div>
        <div v-if="errors.apiError" class="w-100 alert alert-danger mt-3 mb-3">
          {{ errors.apiError }}
        </div>
        <div class="d-flex justify-content-end gap-2">
          <button
            type="button"
            class="btn btn-outline-secondary"
            @click="cancel"
          >
            Cancel
          </button>
          <button
            type="button"
            class="btn btn-success"
            :disabled="!canPreview || status.previewing"
            @click="preview"
          >
            <span v-if="status.previewing">
              <span
                class="spinner-border spinner-border-sm"
                role="status"
                aria-hidden="true"
              ></span>
            </span>
            <span v-else>Preview</span>
          </button>
          <button
            type="submit"
            class="btn btn-primary"
            :disabled="status.creating"
          >
            <span v-if="status.creating">
              <span
                class="spinner-border spinner-border-sm"
                role="status"
                aria-hidden="true"
              ></span>
            </span>
            <span v-else>Add Server</span>
          </button>
        </div>
      </Form>
    </div>
  </div>
  <PreviewPullModal
    v-if="previewOpen"
    :result="previewResult"
    :error="previewError"
    @close="previewOpen = false"
  />
</template>
