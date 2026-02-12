<script setup>
import { reactive, watch } from "vue";
import DistributionLevelSelect from "../enums/DistributionLevelSelect.vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faLink } from "@fortawesome/free-solid-svg-icons";
import { FeedSchema } from "@/schemas/feed";
import { Form, Field } from "vee-validate";

const props = defineProps({
  modelValue: {
    type: Object,
    required: true,
  },
});

const emit = defineEmits(["update:modelValue"]);

const local = reactive({
  name: "Cloudflare IPs",
  url: "https://www.cloudflare.com/ips-v4/",
  provider: "Cloudflare",
  distribution: "0",
  enabled: true,
  description: "",
  input_source: "network",
  schedule: "daily",
  fetch_on_create: true,
});

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

        <div class="col-md-2">
          <label class="form-label" for="feed.input_source">Source</label>
          <Field
            class="form-control"
            id="feed.input_source"
            name="feed.input_source"
            as="select"
            v-model="local.input_source"
            :class="{ 'is-invalid': errors['feed.input_source'] }"
          >
            <option value="network">Network</option>
            <option value="local" disabled>Local</option>
          </Field>
          <div class="invalid-feedback">{{ errors["feed.input_source"] }}</div>
        </div>

        <div class="col-10">
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

        <div class="col-md-6">
          <label class="form-label">Update interval</label>
          <select class="form-select" v-model="local.schedule">
            <option value="hourly">Hourly</option>
            <option value="daily">Daily</option>
            <option value="weekly">Weekly</option>
            <option value="manual" disabled>Manual</option>
          </select>
        </div>

        <div class="col-md-6 d-flex align-items-end">
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
      </div>
    </Form>
  </div>
</template>
