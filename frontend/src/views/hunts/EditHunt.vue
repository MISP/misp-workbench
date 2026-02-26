<script setup>
import { ref, reactive, computed } from "vue";
import { router } from "@/router";
import { useHuntsStore, useToastsStore } from "@/stores";
import { storeToRefs } from "pinia";
import Spinner from "@/components/misc/Spinner.vue";

const props = defineProps({ id: { type: String, required: true } });

const huntsStore = useHuntsStore();
const toastsStore = useToastsStore();
const { hunt, status } = storeToRefs(huntsStore);

const form = reactive({
  name: "",
  description: "",
  query: "",
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
        <div class="form-text text-muted">
          Standard Lucene query string syntax supported.
        </div>
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
