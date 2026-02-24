<script setup>
import { ref, reactive, watch } from "vue";
import TagsSelect from "@/components/tags/TagsSelect.vue";
import OrganisationsMultiSelect from "@/components/organisations/OrganisationsMultiSelect.vue";

const props = defineProps({
  modelValue: { type: [Object, null], required: true },
});

const emit = defineEmits(["update:modelValue"]);

const mode = ref("basic");

const basic = reactive({
  timestamp: { enabled: false, value: 30, unit: "d" },
  tags: { enabled: false, tags: [] },
  orgs: { enabled: false, orgs: [] },
});

const advancedJson = ref("");

// Seed basic controls from the incoming model value
const existing = props.modelValue ?? {};
if (existing.timestamp) {
  const ts = String(existing.timestamp);
  const unit = ts.slice(-1);
  const value = parseInt(ts.slice(0, -1));
  basic.timestamp.enabled = true;
  if (!isNaN(value) && ["d", "w", "m"].includes(unit)) {
    basic.timestamp.value = value;
    basic.timestamp.unit = unit;
  }
}
if (existing.tags?.length) {
  basic.tags.enabled = true;
  basic.tags.tags = [...existing.tags];
}
if (existing.orgs?.length) {
  basic.orgs.enabled = true;
  basic.orgs.orgs = [...existing.orgs];
}

watch(
  [mode, basic, advancedJson],
  () => {
    let rules = {};

    if (mode.value === "basic") {
      if (basic.timestamp.enabled) {
        rules.timestamp = `${basic.timestamp.value}${basic.timestamp.unit}`;
      }
      if (basic.tags.enabled && basic.tags.tags.length > 0) {
        rules.tags = basic.tags.tags;
      }
      if (basic.orgs.enabled && basic.orgs.orgs.length > 0) {
        rules.orgs = basic.orgs.orgs;
      }
    } else {
      try {
        rules = advancedJson.value ? JSON.parse(advancedJson.value) : {};
      } catch {
        return;
      }
    }

    emit("update:modelValue", rules);
  },
  { deep: true },
);
</script>

<template>
  <div class="card">
    <div class="card-header">
      <h5 class="mb-0">Pull Rules</h5>
    </div>

    <div class="card-body">
      <p class="text-muted">
        Define rules to filter which events are pulled from this remote server.
      </p>

      <!-- Mode selector -->
      <div class="mb-3">
        <div class="form-check form-check-inline">
          <input
            class="form-check-input"
            type="radio"
            name="pullRulesMode"
            value="basic"
            v-model="mode"
            id="pullRulesBasic"
          />
          <label class="form-check-label" for="pullRulesBasic">Basic</label>
        </div>
        <div class="form-check form-check-inline">
          <input
            class="form-check-input"
            type="radio"
            name="pullRulesMode"
            value="advanced"
            v-model="mode"
            id="pullRulesAdvanced"
          />
          <label class="form-check-label" for="pullRulesAdvanced">
            Advanced (JSON)
          </label>
        </div>
      </div>

      <!-- BASIC MODE -->
      <div v-if="mode === 'basic'" class="border rounded p-3">
        <!-- Timestamp -->
        <div class="form-check mb-3">
          <input
            class="form-check-input"
            type="checkbox"
            v-model="basic.timestamp.enabled"
            id="pullTimestampRule"
          />
          <label class="form-check-label" for="pullTimestampRule">
            Only pull events published after a given time
          </label>
          <div class="form-text text-muted">
            Events older than the specified range will be skipped.
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

        <!-- Tags -->
        <div class="form-check mb-3">
          <input
            class="form-check-input"
            type="checkbox"
            v-model="basic.tags.enabled"
            id="pullTagsRule"
          />
          <label class="form-check-label" for="pullTagsRule">
            Only pull events with specific tags
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

        <!-- Orgs -->
        <div class="form-check mb-3">
          <input
            class="form-check-input"
            type="checkbox"
            v-model="basic.orgs.enabled"
            id="pullOrgsRule"
          />
          <label class="form-check-label" for="pullOrgsRule">
            Only pull events from specific organisations
          </label>
          <div class="row g-2 mt-2" v-if="basic.orgs.enabled">
            <OrganisationsMultiSelect
              :selectedOrgs="basic.orgs.orgs"
              @update:selectedOrgs="basic.orgs.orgs = $event"
            />
          </div>
        </div>
      </div>

      <!-- ADVANCED MODE -->
      <div v-else>
        <textarea
          class="form-control font-monospace"
          rows="8"
          v-model="advancedJson"
          :placeholder="JSON.stringify(modelValue ?? {}, null, 2)"
        />
        <div class="alert alert-info mt-2">
          <p class="mb-1">Supported rules:</p>
          <ul class="mb-0">
            <li>
              <code>timestamp</code>: Only pull events newer than a given time.
              Format: a number followed by <code>d</code> (days),
              <code>w</code> (weeks) or <code>m</code> (months), or a Unix
              timestamp.
            </li>
            <li>
              <code>tags</code>: Only pull events matching specific tags.
              Example: <code>["tlp:white", "type:OSINT"]</code>.
            </li>
            <li>
              <code>orgs</code>: Only pull events from specific organisations.
              Example: <code>["CIRCL", "FIRST.ORG"]</code>.
            </li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>
