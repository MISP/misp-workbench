<script setup>
import { ref, reactive, watch } from "vue";
import TagsSelect from "@/components/tags/TagsSelect.vue";
import OrganisationsMultiSelect from "@/components/organisations/OrganisationsMultiSelect.vue";

const DEFAULT_FEED_RULES = {
  typeConfig: {
    rules: {
      timestamp: "30d",
    },
  },
};

const props = defineProps({
  modelValue: {
    type: [Object, null],
    required: true,
  },
});

const emit = defineEmits(["update:modelValue"]);

const mode = ref("basic");

const basic = reactive({
  timestamp: {
    enabled: true,
    value: 30,
    unit: "d",
  },
  tags: {
    enabled: false,
    tags: [],
  },
  orgs: {
    enabled: false,
    orgs: [],
  },
});

const advancedJson = ref("");

/**
 * Emit rules depending on mode
 */
watch(
  [mode, basic, advancedJson],
  () => {
    let rules = null;

    if (mode.value === "basic") {
      if (basic.timestamp.enabled) {
        rules = {
          timestamp: `${basic.timestamp.value}${basic.timestamp.unit}`,
        };
      }
      if (basic.tags.enabled && basic.tags.tags.length > 0) {
        if (!rules) {
          rules = {};
        }
        rules.tags = basic.tags.tags;
      }
      if (basic.orgs.enabled && basic.orgs.orgs.length > 0) {
        if (!rules) {
          rules = {};
        }
        rules.orgs = basic.orgs.orgs;
      }
    } else {
      try {
        rules = advancedJson.value ? JSON.parse(advancedJson.value) : null;
      } catch {
        // Invalid JSON
        return;
      }
    }

    emit("update:modelValue", { typeConfig: rules ? { rules } : {} });
  },
  { deep: true },
);

if (
  props.modelValue.typeConfig === null ||
  Object.keys(props.modelValue.typeConfig).length === 0
) {
  emit("update:modelValue", DEFAULT_FEED_RULES);
}
</script>

<template>
  <div class="card">
    <div class="card-header">
      <h5 class="mb-0">MISP Feed Rules</h5>
    </div>

    <div class="card-body">
      <p class="text-muted">
        Define rules to limit which events are fetched from the remote MISP
        instance.
      </p>

      <!-- Mode selector -->
      <div class="mb-3">
        <div class="form-check form-check-inline">
          <input
            class="form-check-input"
            type="radio"
            name="rulesMode"
            value="basic"
            v-model="mode"
            id="rulesBasic"
          />
          <label class="form-check-label" for="rulesBasic"> Basic </label>
        </div>

        <div class="form-check form-check-inline">
          <input
            class="form-check-input"
            type="radio"
            name="rulesMode"
            value="advanced"
            v-model="mode"
            id="rulesAdvanced"
          />
          <label class="form-check-label" for="rulesAdvanced">
            Advanced (JSON)
          </label>
        </div>
      </div>

      <!-- BASIC MODE -->
      <div v-if="mode === 'basic'">
        <div class="border rounded p-3">
          <div class="form-check mb-3">
            <input
              class="form-check-input"
              type="checkbox"
              v-model="basic.timestamp.enabled"
              id="timestampRule"
            />
            <label class="form-check-label" for="timestampRule">
              Only fetch events published after a given time
            </label>
            <div class="form-text text-muted">
              Events older than the specified time range will be ignored during
              ingestion.
            </div>
            <div class="row g-2 mt-2" v-if="basic.timestamp.enabled">
              <div class="col-md-6">
                <label class="form-label">Time range</label>
                <input
                  type="number"
                  min="1"
                  class="form-control"
                  v-model.number="basic.timestamp.value"
                />
              </div>

              <div class="col-md-6">
                <label class="form-label">Unit</label>
                <select class="form-select" v-model="basic.timestamp.unit">
                  <option value="d">Days</option>
                  <option value="w">Weeks</option>
                  <option value="m">Months</option>
                </select>
              </div>
            </div>
          </div>
          <div v-if="!basic.timestamp.enabled" class="alert alert-danger mt-2">
            Be cautious when disabling this option on feeds with a lot of data,
            as it may result in fetching a large number of events initially.
          </div>
          <div class="form-check mb-3">
            <input
              class="form-check-input"
              type="checkbox"
              v-model="basic.tags.enabled"
              id="tagsRule"
            />
            <label class="form-check-label" for="tagsRule">
              Only fetch events with specific tags
            </label>
            <div class="row g-2 mt-2" v-if="basic.tags.enabled">
              <TagsSelect
                :modelClass="'event'"
                :model="basic.tags.tags"
                :persist="false"
                @update:selectedTags="basic.tags.tags = $event"
              />
            </div>
          </div>
          <div class="form-check mb-3">
            <input
              class="form-check-input"
              type="checkbox"
              v-model="basic.orgs.enabled"
              id="orgsRule"
            />
            <label class="form-check-label" for="orgsRule">
              Only fetch events from specific organisations
            </label>
            <div class="row g-2 mt-2" v-if="basic.orgs.enabled">
              <OrganisationsMultiSelect
                @update:selectedOrgs="basic.orgs.orgs = $event"
              />
            </div>
          </div>
        </div>
      </div>

      <!-- ADVANCED MODE -->
      <div v-else>
        <textarea
          class="form-control font-monospace"
          rows="8"
          v-model="advancedJson"
          placeholder='{
  "timestamp": "30d"
}'
        />
        <div class="alert alert-info mt-2">
          <p>
            Advanced mode allows you to define the rules object directly.
            Invalid JSON or unsupported rules may cause feed ingestion to fail
            or behave unexpectedly.
          </p>
          <p>
            Use the <strong>Test Connection</strong> button to validate your
            rules before saving.
          </p>
          <p>Supported rules are:</p>
          <ul>
            <li>
              <code>timestamp</code>: Only fetch events published after a given
              time. Format can be a number followed by a unit, where unit can be
              <code>d</code> (days), <code>w</code> (weeks) or
              <code>m</code> (months). Example:
              <code>"timestamp": "30d"</code> or a Unix timestamp.
            </li>
            <li>
              <code>tags</code>: Only fetch events with specific tags. Format is
              an array of tag names. Example:
              <code>"tags": ["tlp:white", "type:OSINT"]</code>.
            </li>
            <li>
              <code>orgs</code>: Only fetch events from specific organisations.
              Format is an array of organisation names. Example:
              <code>"orgs": ["CIRCL", "FIRST.ORG"]</code>.
            </li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>
