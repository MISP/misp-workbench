<script setup>
import { ref, reactive, computed } from "vue";
import { router } from "@/router";
import { useHuntsStore, useToastsStore } from "@/stores";
import { storeToRefs } from "pinia";
import Spinner from "@/components/misc/Spinner.vue";
import LuceneQuerySyntaxHint from "@/components/misc/LuceneQuerySyntaxHint.vue";

const props = defineProps({ id: { type: String, required: true } });

const huntsStore = useHuntsStore();
const toastsStore = useToastsStore();
const { hunt, status } = storeToRefs(huntsStore);

const form = reactive({
  name: "",
  description: "",
  query: "",
  hunt_type: "opensearch",
  index_target: "attributes",
  status: "active",
});

const apiError = ref(null);
const loaded = ref(false);

huntsStore.getById(props.id).then(() => {
  Object.assign(form, hunt.value);
  loaded.value = true;
});

const canSubmit = computed(() => form.name && form.query);

async function submit() {
  apiError.value = null;
  await huntsStore
    .update(props.id, { ...form })
    .then(() => {
      toastsStore.push("Hunt updated.", "success");
      router.push(`/hunts/${props.id}`);
    })
    .catch((err) => (apiError.value = err?.message || String(err)));
}

function cancel() {
  router.push(`/hunts/${props.id}`);
}
</script>

<template>
  <Spinner v-if="status.loading && !loaded" />
  <div v-else class="card mx-auto" style="max-width: 720px">
    <div class="card-header border-bottom">
      <h4 class="mb-0">Edit Hunt</h4>
    </div>
    <div class="card-body">
      <div class="mb-3">
        <label class="form-label" for="hunt-name">Name</label>
        <input id="hunt-name" class="form-control" v-model="form.name" />
      </div>

      <div class="mb-3">
        <label class="form-label" for="hunt-description">Description</label>
        <textarea
          id="hunt-description"
          class="form-control"
          rows="2"
          v-model="form.description"
        />
      </div>

      <div class="mb-3">
        <label class="form-label">Hunt Type</label>
        <div>
          <span class="badge bg-secondary">{{ form.hunt_type }}</span>
        </div>
      </div>

      <template v-if="form.hunt_type === 'opensearch'">
        <div class="mb-3">
          <label class="form-label" for="hunt-target">Search index</label>
          <select
            id="hunt-target"
            class="form-select"
            v-model="form.index_target"
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
            v-model="form.query"
          />
          <LuceneQuerySyntaxHint />
          <div
            v-if="form.index_target === 'correlations'"
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

      <div v-else-if="form.hunt_type === 'rulezet'" class="mb-3">
        <label class="form-label" for="hunt-cve">Vuln ID</label>
        <input
          id="hunt-cve"
          class="form-control font-monospace"
          v-model="form.query"
          placeholder="CVE-2024-1234"
        />
      </div>

      <div v-else-if="form.hunt_type === 'cpe'" class="mb-3">
        <label class="form-label" for="hunt-cpe">CPE string</label>
        <input
          id="hunt-cpe"
          class="form-control font-monospace"
          v-model="form.query"
          placeholder="cpe:/a:gitlab:gitlab"
        />
      </div>

      <template v-else-if="form.hunt_type === 'mitre-attack-pattern'">
        <div class="mb-3">
          <label class="form-label" for="hunt-mitre-target">Search index</label>
          <select
            id="hunt-mitre-target"
            class="form-select"
            v-model="form.index_target"
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
          <textarea
            id="hunt-mitre"
            class="form-control font-monospace"
            rows="3"
            v-model="form.query"
            placeholder="T1391, T1078.004"
          />
          <div class="form-text">
            MITRE ATT&amp;CK technique codes (e.g. <code>T1391</code>,
            <code>T1078.004</code>), comma or newline separated.
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
            :checked="form.status === 'active'"
            @change="form.status = $event.target.checked ? 'active' : 'paused'"
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
          :disabled="!canSubmit || status.updating"
          @click="submit"
        >
          {{ status.updating ? "Saving…" : "Save Changes" }}
        </button>
      </div>
    </div>
  </div>
</template>
