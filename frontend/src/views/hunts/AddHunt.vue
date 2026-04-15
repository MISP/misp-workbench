<script setup>
import { ref, reactive, computed } from "vue";
import { router } from "@/router";
import { useHuntsStore, useToastsStore } from "@/stores";
import LuceneQuerySyntaxHint from "@/components/misc/LuceneQuerySyntaxHint.vue";
import MitreAttackSelect from "@/components/hunts/MitreAttackSelect.vue";
import HuntTypeSelector from "@/components/hunts/HuntTypeSelector.vue";

const huntsStore = useHuntsStore();
const toastsStore = useToastsStore();

const hunt = reactive({
  name: "",
  description: "",
  query: "",
  hunt_type: "opensearch",
  index_target: "attributes",
  status: "active",
});

function onHuntTypeChange() {
  if (hunt.hunt_type === "mitre-attack-pattern") {
    if (
      !["attributes", "events", "attributes_and_events"].includes(
        hunt.index_target,
      )
    ) {
      hunt.index_target = "attributes_and_events";
    }
  } else if (hunt.hunt_type === "opensearch") {
    if (hunt.index_target === "attributes_and_events") {
      hunt.index_target = "attributes";
    }
  }
}

const apiError = ref(null);

const canSubmit = computed(() => hunt.name && hunt.query);

async function submit() {
  apiError.value = null;
  await huntsStore
    .create({ ...hunt })
    .then((response) => {
      toastsStore.push(`Hunt "${response.name}" created.`, "success");
      router.push(`/hunts/${response.id}`);
    })
    .catch((err) => (apiError.value = err?.message || String(err)));
}

function cancel() {
  router.push("/hunts");
}
</script>

<template>
  <div class="card mx-auto" style="max-width: 720px">
    <div class="card-header border-bottom">
      <h4 class="mb-0">New Hunt</h4>
    </div>
    <div class="card-body">
      <p class="text-muted mb-4">
        A hunt periodically checks for new matches and notifies you when the
        count changes.
      </p>

      <div class="mb-3">
        <label class="form-label">Hunt Type</label>
        <HuntTypeSelector
          v-model="hunt.hunt_type"
          @update:modelValue="onHuntTypeChange"
        />
      </div>

      <div class="mb-3">
        <label class="form-label" for="hunt-name">Name</label>
        <input
          id="hunt-name"
          class="form-control"
          v-model="hunt.name"
          :placeholder="
            hunt.hunt_type === 'opensearch'
              ? 'e.g. Suspicious IPs'
              : 'e.g. SharePoint RCE CVEs'
          "
        />
      </div>

      <div class="mb-3">
        <label class="form-label" for="hunt-description">Description</label>
        <textarea
          id="hunt-description"
          class="form-control"
          rows="2"
          v-model="hunt.description"
          placeholder="Optional description"
        />
      </div>

      <template v-if="hunt.hunt_type === 'opensearch'">
        <div class="mb-3">
          <label class="form-label" for="hunt-target">Search index</label>
          <select
            id="hunt-target"
            class="form-select"
            v-model="hunt.index_target"
          >
            <option value="attributes">Attributes</option>
            <option value="events">Events</option>
            <option value="correlations">Correlations</option>
          </select>
        </div>

        <div class="mb-3">
          <label class="form-label" for="hunt-query">Lucene Query</label>
          <textarea
            id="hunt-query"
            class="form-control font-monospace"
            rows="4"
            v-model="hunt.query"
            :placeholder="
              hunt.index_target === 'correlations'
                ? 'e.g. target_attribute_value:192.168.1.1'
                : 'e.g. type:ip-dst AND value:192.168.*'
            "
          />
          <LuceneQuerySyntaxHint />
          <div
            v-if="hunt.index_target === 'correlations'"
            class="alert alert-info mt-2 mb-0 small"
          >
            <strong>Correlation index fields:</strong>
            <code>target_attribute_value</code>,
            <code>target_attribute_type</code>, <code>source_event_uuid</code>,
            <code>target_event_uuid</code>, <code>source_attribute_uuid</code>,
            <code>target_attribute_uuid</code>, <code>match_type</code> (term |
            prefix | fuzzy | cidr),
            <code>score</code>
          </div>
        </div>
      </template>

      <div v-else-if="hunt.hunt_type === 'rulezet'" class="mb-3">
        <label class="form-label" for="hunt-cve">Vuln ID</label>
        <input
          id="hunt-cve"
          class="form-control font-monospace"
          v-model="hunt.query"
          placeholder="e.g. CVE-2024-1234"
        />
      </div>

      <div v-else-if="hunt.hunt_type === 'cpe'" class="mb-3">
        <label class="form-label" for="hunt-cpe">CPE string</label>
        <input
          id="hunt-cpe"
          class="form-control font-monospace"
          v-model="hunt.query"
          placeholder="cpe:/a:gitlab:gitlab"
        />
        <div class="form-text">
          Queries vulnerability.circl.lu for CVEs affecting this CPE. Notifies
          you when the result set changes.
        </div>
      </div>

      <template v-else-if="hunt.hunt_type === 'mitre-attack-pattern'">
        <div class="mb-3">
          <label class="form-label" for="hunt-mitre-target">Search index</label>
          <select
            id="hunt-mitre-target"
            class="form-select"
            v-model="hunt.index_target"
          >
            <option value="attributes_and_events">
              Attributes &amp; Events
            </option>
            <option value="events">Events</option>
            <option value="attributes">Attributes</option>
          </select>
        </div>

        <div class="mb-3">
          <label class="form-label" for="hunt-mitre"
            >MITRE ATT&amp;CK technique</label
          >
          <MitreAttackSelect v-model="hunt.query" />
          <div class="form-text">
            Select one or more MITRE ATT&amp;CK techniques. Matches
            {{
              hunt.index_target === "attributes"
                ? "attributes"
                : hunt.index_target === "events"
                  ? "events"
                  : "attributes and events"
            }}
            tagged with any of these techniques.
          </div>
        </div>
      </template>

      <div class="mb-4">
        <div class="form-check form-switch">
          <input
            class="form-check-input"
            type="checkbox"
            role="switch"
            id="hunt-active"
            :checked="hunt.status === 'active'"
            @change="hunt.status = $event.target.checked ? 'active' : 'paused'"
          />
          <label class="form-check-label" for="hunt-active">Active</label>
        </div>
      </div>

      <div v-if="apiError" class="alert alert-danger">{{ apiError }}</div>

      <div class="d-flex justify-content-end gap-2">
        <button class="btn btn-outline-secondary" @click="cancel">
          Cancel
        </button>
        <button
          class="btn btn-primary"
          :disabled="!canSubmit || huntsStore.status.creating"
          @click="submit"
        >
          {{ huntsStore.status.creating ? "Creating…" : "Create Hunt" }}
        </button>
      </div>
    </div>
  </div>
</template>
