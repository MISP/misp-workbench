<script setup>
import { ref } from "vue";
import { Form, Field } from "vee-validate";
import { storeToRefs } from "pinia";
import { useFeedsStore } from "@/stores";
import { router } from "@/router";
import { FeedSchema } from "@/schemas/feed";
import OrganisationsSelect from "@/components/organisations/OrganisationsSelect.vue";
import DistributionLevelSelect from "@/components/enums/DistributionLevelSelect.vue";

const feedsStore = useFeedsStore();
const { status, error } = storeToRefs(feedsStore);

const feed = {};

const feedRules = ref(JSON.stringify(feed.rules || {}, null, 2));
const feedSettings = ref(JSON.stringify(feed.settings || {}, null, 2));
const feedHeaders = ref(JSON.stringify(feed.headers || {}, null, 2));

function createFeed(values, { setErrors }) {
  feed.rules = JSON.parse(feedRules.value) || {};
  feed.settings = JSON.parse(feedSettings.value) || {};
  feed.headers = JSON.parse(feedHeaders.value) || {};
  return feedsStore
    .create(feed)
    .then((response) => {
      router.push(`/feeds/${response.id}`);
    })
    .catch((error) => setErrors({ apiError: error }));
}

function handleOrganisationUpdated(orgId) {
  feed.org_id = orgId;
}
function handleDistributionLevelUpdated(distributionLevelId) {
  feed.distribution = parseInt(distributionLevelId);
}
</script>

<template>
  <div class="card">
    <div class="card-header border-bottom">
      <div class="row">
        <div class="col-10">
          <h3>Add Feed</h3>
          {{ feed.role_id }}
        </div>
      </div>
    </div>
    <div class="card-body d-flex flex-column">
      <Form
        @submit="createFeed"
        :validation-schema="FeedSchema"
        v-slot="{ errors }"
      >
        <div class="mb-3">
          <label for="feed.name">name</label>
          <Field
            class="form-control"
            id="feed.name"
            name="feed.name"
            v-model="feed.name"
            :class="{ 'is-invalid': errors['feed.name'] }"
          >
          </Field>
          <div class="invalid-feedback">{{ errors["feed.name"] }}</div>
        </div>
        <div class="mb-3">
          <label for="feed.provider">provider</label>
          <Field
            class="form-control"
            id="feed.provider"
            name="feed.provider"
            v-model="feed.provider"
            :class="{ 'is-invalid': errors['feed.provider'] }"
          >
          </Field>
          <div class="invalid-feedback">{{ errors["feed.provider"] }}</div>
        </div>
        <div class="mb-3">
          <label for="feed.url">url</label>
          <Field
            class="form-control"
            id="feed.url"
            name="feed.url"
            v-model="feed.url"
            :class="{ 'is-invalid': errors['feed.url'] }"
          >
          </Field>
          <div class="invalid-feedback">{{ errors["feed.url"] }}</div>
        </div>
        <div class="mb-3">
          <label for="feed.distribution" class="form-label">distribution</label>
          <DistributionLevelSelect
            name="feed.distribution"
            :selected="feed.distribution"
            @distribution-level-updated="handleDistributionLevelUpdated"
            :errors="errors['feed.distribution']"
          />
          <div class="invalid-feedback">{{ errors["feed.distribution"] }}</div>
        </div>
        <!-- TODO: sharing groups -->
        <!-- <div class="row m-2"> -->
        <!-- <div class="col col-6 text-start">
                    <label for="feed.sharing_group_id" class="form-label">Sharing Group</label>
                    <SharingGroupSelect v-model=feed.sharing_group_id />
                    <div class="invalid-feedback">{{ errors[feed.sharing_group_id'] }}</div>
                    </div>
                </div> -->
        <div class="mb-3">
          <label for="feed.source_format">source_format</label>
          <Field
            class="form-control"
            id="feed.source_format"
            name="feed.source_format"
            as="select"
            v-model="feed.source_format"
            :class="{ 'is-invalid': errors['feed.source_format'] }"
          >
            <option value="misp">MISP Feed</option>
            <option value="csv">Freetext Parsed Feed</option>
            <option value="freetext">Simple CSV Parsed Feed</option>
          </Field>
          <div class="invalid-feedback">{{ errors["feed.source_format"] }}</div>
        </div>
        <div class="mb-3">
          <label for="feed.input_source">input_source</label>
          <Field
            class="form-control"
            id="feed.input_source"
            name="feed.input_source"
            as="select"
            v-model="feed.input_source"
            :class="{ 'is-invalid': errors['feed.input_source'] }"
          >
            <option value="network">Network</option>
            <option value="local">Local</option>
          </Field>
          <div class="invalid-feedback">{{ errors["feed.input_source"] }}</div>
        </div>
        <div class="mb-3">
          <label for="feed.enabled">enabled</label>
          <Field
            class="form-control"
            id="feed.enabled"
            name="feed.enabled"
            :value="feed.enabled"
            v-model="feed.enabled"
            :class="{ 'is-invalid': errors['feed.enabled'] }"
          >
            <div class="form-check">
              <input
                class="form-check-input"
                type="checkbox"
                v-model="feed.enabled"
              />
            </div>
          </Field>
          <div class="invalid-feedback">{{ errors["feed.enabled"] }}</div>
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
          <div class="col-md-6">
            <div class="mb-3">
              <label for="feed.rules">rules</label>
              <Field
                class="form-control"
                id="feed.rules"
                name="feed.rules"
                as="textarea"
                cols="40"
                rows="5"
                v-model="feedRules"
                :class="{ 'is-invalid': errors['feed.rules'] }"
              >
              </Field>
              <div class="invalid-feedback">{{ errors["feed.rules"] }}</div>
            </div>
          </div>
          <div class="col-md-6">
            <div class="mb-3">
              <label for="feed.headers">headers</label>
              <Field
                class="form-control"
                id="feed.headers"
                name="feed.headers"
                as="textarea"
                cols="40"
                rows="2"
                v-model="feedHeaders"
                :class="{ 'is-invalid': errors['feed.headers'] }"
              >
              </Field>
              <div class="invalid-feedback">{{ errors["feed.headers"] }}</div>
            </div>
          </div>
          <div class="col-md-6">
            <div class="mb-3">
              <label for="feed.settings">settings</label>
              <Field
                class="form-control"
                id="feed.settings"
                name="feed.settings"
                as="textarea"
                cols="40"
                rows="2"
                v-model="feedSettings"
                :class="{ 'is-invalid': errors['feed.settings'] }"
              >
              </Field>
              <div class="invalid-feedback">{{ errors["feed.settings"] }}</div>
            </div>
          </div>
          <div class="mb-3">
            <label for="feed.tag_id">tag_id</label>
            <Field
              class="form-control"
              id="feed.tag_id"
              name="feed.tag_id"
              v-model="feed.tag_id"
              :class="{ 'is-invalid': errors['feed.tag_id'] }"
            >
            </Field>
            <div class="invalid-feedback">{{ errors["feed.tag_id"] }}</div>
          </div>
          <div class="mb-3">
            <label for="feed.default">default</label>
            <Field
              class="form-control"
              id="feed.default"
              name="feed.default"
              :value="feed.default"
              v-model="feed.default"
              :class="{ 'is-invalid': errors['feed.default'] }"
            >
              <div class="form-check">
                <input
                  class="form-check-input"
                  type="checkbox"
                  v-model="feed.default"
                />
              </div>
            </Field>
            <div class="invalid-feedback">{{ errors["feed.default"] }}</div>
          </div>
          <div class="mb-3">
            <label for="feed.fixed_event">fixed_event</label>
            <Field
              class="form-control"
              id="feed.fixed_event"
              name="feed.fixed_event"
              :value="feed.fixed_event"
              v-model="feed.fixed_event"
              :class="{ 'is-invalid': errors['feed.fixed_event'] }"
            >
              <div class="form-check">
                <input
                  class="form-check-input"
                  type="checkbox"
                  v-model="feed.fixed_event"
                />
              </div>
            </Field>
            <div class="invalid-feedback">{{ errors["feed.fixed_event"] }}</div>
          </div>
          <div class="mb-3">
            <label for="feed.delta_merge">delta_merge</label>
            <Field
              class="form-control"
              id="feed.delta_merge"
              name="feed.delta_merge"
              :value="feed.delta_merge"
              v-model="feed.delta_merge"
              :class="{ 'is-invalid': errors['feed.delta_merge'] }"
            >
              <div class="form-check">
                <input
                  class="form-check-input"
                  type="checkbox"
                  v-model="feed.delta_merge"
                />
              </div>
            </Field>
            <div class="invalid-feedback">{{ errors["feed.delta_merge"] }}</div>
          </div>
          <div class="mb-3">
            <label for="feed.event_id">event_id</label>
            <Field
              class="form-control"
              id="feed.event_id"
              name="feed.event_id"
              v-model="feed.event_id"
              :class="{ 'is-invalid': errors['feed.event_id'] }"
            >
            </Field>
            <div class="invalid-feedback">{{ errors["feed.event_id"] }}</div>
          </div>
          <div class="mb-3">
            <label for="feed.publish">publish</label>
            <Field
              class="form-control"
              id="feed.publish"
              name="feed.publish"
              :value="feed.publish"
              v-model="feed.publish"
              :class="{ 'is-invalid': errors['feed.publish'] }"
            >
              <div class="form-check">
                <input
                  class="form-check-input"
                  type="checkbox"
                  v-model="feed.publish"
                />
              </div>
            </Field>
            <div class="invalid-feedback">{{ errors["feed.publish"] }}</div>
          </div>
          <div class="mb-3">
            <label for="feed.override_ids">override_ids</label>
            <Field
              class="form-control"
              id="feed.override_ids"
              name="feed.override_ids"
              :value="feed.override_ids"
              v-model="feed.override_ids"
              :class="{ 'is-invalid': errors['feed.override_ids'] }"
            >
              <div class="form-check">
                <input
                  class="form-check-input"
                  type="checkbox"
                  v-model="feed.override_ids"
                />
              </div>
            </Field>
            <div class="invalid-feedback">
              {{ errors["feed.override_ids"] }}
            </div>
          </div>
          <div class="mb-3">
            <label for="feed.delete_local_file">delete_local_file</label>
            <Field
              class="form-control"
              id="feed.delete_local_file"
              name="feed.delete_local_file"
              :value="feed.delete_local_file"
              v-model="feed.delete_local_file"
              :class="{ 'is-invalid': errors['feed.delete_local_file'] }"
            >
              <div class="form-check">
                <input
                  class="form-check-input"
                  type="checkbox"
                  v-model="feed.delete_local_file"
                />
              </div>
            </Field>
            <div class="invalid-feedback">
              {{ errors["feed.delete_local_file"] }}
            </div>
          </div>
          <div class="mb-3">
            <label for="feed.lookup_visible">lookup_visible</label>
            <Field
              class="form-control"
              id="feed.lookup_visible"
              name="feed.lookup_visible"
              :value="feed.lookup_visible"
              v-model="feed.lookup_visible"
              :class="{ 'is-invalid': errors['feed.lookup_visible'] }"
            >
              <div class="form-check">
                <input
                  class="form-check-input"
                  type="checkbox"
                  v-model="feed.lookup_visible"
                />
              </div>
            </Field>
            <div class="invalid-feedback">
              {{ errors["feed.lookup_visible"] }}
            </div>
          </div>
          <div class="mb-3">
            <label for="feed.caching_enabled">caching_enabled</label>
            <Field
              class="form-control"
              id="feed.caching_enabled"
              name="feed.caching_enabled"
              :value="feed.caching_enabled"
              v-model="feed.caching_enabled"
              :class="{ 'is-invalid': errors['feed.caching_enabled'] }"
            >
              <div class="form-check">
                <input
                  class="form-check-input"
                  type="checkbox"
                  v-model="feed.caching_enabled"
                />
              </div>
            </Field>
            <div class="invalid-feedback">
              {{ errors["feed.caching_enabled"] }}
            </div>
          </div>
          <div class="mb-3">
            <label for="feed.force_to_ids">force_to_ids</label>
            <Field
              class="form-control"
              id="feed.force_to_ids"
              name="feed.force_to_ids"
              :value="feed.force_to_ids"
              v-model="feed.force_to_ids"
              :class="{ 'is-invalid': errors['feed.force_to_ids'] }"
            >
              <div class="form-check">
                <input
                  class="form-check-input"
                  type="checkbox"
                  v-model="feed.force_to_ids"
                />
              </div>
            </Field>
            <div class="invalid-feedback">
              {{ errors["feed.force_to_ids"] }}
            </div>
          </div>
          <div class="mb-3">
            <label for="feed.orgc_id">organisation</label>
            <OrganisationsSelect
              name="feed.org_id"
              :selected="feed.orgc_id"
              @organisation-updated="handleOrganisationUpdated"
              :errors="errors['feed.orgc_id']"
            />
            <div class="invalid-feedback">{{ errors["feed.orgc_id"] }}</div>
          </div>
          <div class="mb-3">
            <label for="feed.tag_collection_id">tag_collection_id</label>
            <Field
              class="form-control"
              id="feed.tag_collection_id"
              name="feed.tag_collection_id"
              v-model="feed.tag_collection_id"
              :class="{ 'is-invalid': errors['feed.tag_collection_id'] }"
            >
            </Field>
            <div class="invalid-feedback">
              {{ errors["feed.tag_collection_id"] }}
            </div>
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
