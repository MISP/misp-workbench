<script setup>
import { computed, reactive, watch } from "vue";
import DistributionLevelSelect from "../enums/DistributionLevelSelect.vue";
import FeedFileUpload from "@/components/feeds/FeedFileUpload.vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faLink } from "@fortawesome/free-solid-svg-icons";
import { FeedSchema } from "@/schemas/feed";
import { Form, Field } from "vee-validate";

const props = defineProps({
  modelValue: {
    type: Object,
    required: true,
  },
  sourceFormat: {
    type: String,
    default: "misp",
  },
});

const emit = defineEmits(["update:modelValue"]);

const local = reactive({
  name: "",
  url: "",
  provider: "",
  distribution: "0",
  enabled: true,
  fixed_event: true,
  description: "",
  input_source: "network",
  schedule: "86400",
  fetch_on_create: true,
  headers: {},
  settings: {},
  ...props.modelValue,
});

const isLocal = computed(() => local.input_source === "local");

const localFile = computed(() => (local.settings || {}).localFile || {});

watch(
  () => local.input_source,
  (next, prev) => {
    if (next === prev) return;
    if (next === "local") {
      local.schedule = "disabled";
      local.url = "";
    } else {
      const nextSettings = { ...(local.settings || {}) };
      delete nextSettings.localFile;
      local.settings = nextSettings;
      local.url = "";
    }
  },
);

function onFileUploaded({ key, filename, size }) {
  local.url = key;
  local.settings = {
    ...(local.settings || {}),
    localFile: { filename, size },
  };
}

function onFileCleared() {
  local.url = "";
  const next = { ...(local.settings || {}) };
  delete next.localFile;
  local.settings = next;
}

const auth = reactive({
  type: "none",
  header_name: "Authorization",
  header_value: "",
});

watch(
  auth,
  () => {
    if (auth.type === "header" && auth.header_name && auth.header_value) {
      local.headers = { [auth.header_name]: auth.header_value };
    } else {
      local.headers = {};
    }
  },
  { deep: true },
);

/**
 * Sync incoming modelValue → local state
 */
watch(
  () => props.modelValue,
  (value) => {
    Object.assign(local, value);
  },
  { deep: true },
);

/**
 * Emit local changes → parent
 */
watch(
  local,
  () => {
    emit("update:modelValue", { ...local });
  },
  { deep: true },
);

function handleDistributionLevelUpdated(distributionLevelId) {
  local.distribution = parseInt(distributionLevelId);
}
</script>

<template>
  <div class="feed-base-form">
    <Form :validation-schema="FeedSchema" v-slot="{ errors }">
      <div class="row g-3">
        <div class="col-md-6">
          <label class="form-label" for="feed.name">Name</label>
          <Field
            class="form-control"
            id="feed.name"
            name="feed.name"
            v-model="local.name"
            :class="{ 'is-invalid': errors['feed.name'] }"
          >
          </Field>
          <div class="invalid-feedback">{{ errors["feed.name"] }}</div>
        </div>
        <div class="col-md-6 d-flex align-items-end">
          <Field
            class="form-control"
            id="feed.enabled"
            name="feed.enabled"
            :value="local.enabled"
            v-model="local.enabled"
            :class="{ 'is-invalid': errors['feed.enabled'] }"
          >
            <div class="form-check form-switch">
              <input
                class="form-check-input"
                type="checkbox"
                v-model="local.enabled"
                id="feedEnabled"
              />
              <label class="form-check-label" for="feedEnabled">
                Enabled
              </label>
            </div>
          </Field>
          <div class="invalid-feedback">{{ errors["feed.enabled"] }}</div>
        </div>
        <div class="col-md-6">
          <label class="form-label" for="feed.provider">Provider</label>
          <Field
            class="form-control"
            id="feed.provider"
            name="feed.provider"
            v-model="local.provider"
            :class="{ 'is-invalid': errors['feed.provider'] }"
          >
          </Field>
          <div class="invalid-feedback">{{ errors["feed.provider"] }}</div>
        </div>

        <div class="col-md-6">
          <label for="feed.distribution" class="form-label">Distribution</label>
          <DistributionLevelSelect
            name="feed.distribution"
            :selected="local.distribution"
            @distribution-level-updated="handleDistributionLevelUpdated"
            :errors="errors['feed.distribution']"
          />
          <div class="invalid-feedback">{{ errors["feed.distribution"] }}</div>
        </div>

        <div class="col-md-12">
          <label class="form-label">Input source</label>
          <div class="d-flex gap-3">
            <div class="form-check">
              <input
                class="form-check-input"
                type="radio"
                id="inputSourceNetwork"
                value="network"
                v-model="local.input_source"
              />
              <label class="form-check-label" for="inputSourceNetwork">
                Network (fetch from URL)
              </label>
            </div>
            <div class="form-check">
              <input
                class="form-check-input"
                type="radio"
                id="inputSourceLocal"
                value="local"
                v-model="local.input_source"
              />
              <label class="form-check-label" for="inputSourceLocal">
                Upload file
              </label>
            </div>
          </div>
        </div>

        <div v-if="!isLocal" class="col-10">
          <label class="form-label" for="feed.url">URI</label>
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
              id="feed.url"
              name="feed.url"
              v-model="local.url"
              :class="{ 'is-invalid': errors['feed.url'] }"
            >
            </Field>
            <div class="invalid-feedback">{{ errors["feed.url"] }}</div>
          </div>
        </div>

        <div v-else class="col-12">
          <label class="form-label">File</label>
          <FeedFileUpload
            :source-format="sourceFormat"
            :filename="localFile.filename"
            :size="localFile.size"
            :storage-key="local.url"
            @uploaded="onFileUploaded"
            @cleared="onFileCleared"
          />
        </div>

        <div v-if="!isLocal" class="col-12">
          <label class="form-label">Authentication</label>
          <select class="form-select mb-2" v-model="auth.type">
            <option value="none">No Authentication</option>
            <option value="header">Auth Header</option>
          </select>
          <div v-if="auth.type === 'header'" class="row g-2">
            <div class="col-md-4">
              <label class="form-label small text-muted">Header Name</label>
              <input
                class="form-control"
                type="text"
                v-model="auth.header_name"
                placeholder="Authorization"
              />
            </div>
            <div class="col-md-8">
              <label class="form-label small text-muted">Secret</label>
              <input
                class="form-control"
                type="password"
                v-model="auth.header_value"
                placeholder="Bearer token123"
              />
            </div>
          </div>
        </div>

        <div class="col-md-12">
          <Field
            class="form-control"
            id="feed.enabled"
            name="feed.fixed_event"
            :value="local.fixed_event"
            v-model="local.fixed_event"
            :class="{ 'is-invalid': errors['feed.fixed_event'] }"
          >
            <div class="form-check form-switch">
              <input
                class="form-check-input"
                type="checkbox"
                v-model="local.fixed_event"
                id="feedFixedEvent"
              />
              <label class="form-check-label" for="feedFixedEvent">
                Fixed Event
              </label>
            </div>
          </Field>
          <div class="form-text text-muted">
            If enabled, all attributes from this feed will be associated with a
            single fixed event. Otherwise, a new event will be created for each
            fetch.
          </div>
          <div class="invalid-feedback">{{ errors["feed.fixed_event"] }}</div>
        </div>

        <div v-if="!isLocal" class="col-md-6">
          <label class="form-label">Update interval</label>
          <select class="form-select" v-model="local.schedule">
            <option value="3600">Hourly</option>
            <option value="86400">Daily</option>
            <option value="604800">Weekly</option>
            <option value="disabled">No automatic updates</option>
          </select>
        </div>

        <div v-if="!isLocal" class="col-md-6 d-flex align-items-end">
          <div class="form-check">
            <input
              class="form-check-input"
              type="checkbox"
              v-model="local.fetch_on_create"
              id="fetchOnCreate"
            />
            <label class="form-check-label" for="fetchOnCreate">
              Fetch immediately after creation
            </label>
          </div>
        </div>

        <div v-else class="col-12 text-muted small">
          Uploaded feeds are ingested once when the feed is created. Replace the
          file on the Update Feed page to re-ingest later.
        </div>
      </div>
    </Form>
  </div>
</template>
