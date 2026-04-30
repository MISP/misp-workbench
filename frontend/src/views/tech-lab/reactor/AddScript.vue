<script setup>
import { ref, reactive, computed } from "vue";
import { router } from "@/router";
import { useReactorStore, useToastsStore } from "@/stores";

const reactorStore = useReactorStore();
const toastsStore = useToastsStore();

const RESOURCE_OPTIONS = [
  "event",
  "attribute",
  "object",
  "correlation",
  "sighting",
];
const ACTION_OPTIONS = [
  "created",
  "updated",
  "deleted",
  "published",
  "unpublished",
];

const DEFAULT_SOURCE = `def handle(ctx, payload):
    """Called for every matching trigger.

    ``ctx`` exposes get_event/get_attribute/add_attribute/tag_event/tag_attribute.
    ``payload`` is the entity the trigger fired on (dict).
    """
    ctx.log("triggered with payload", payload)
`;

const script = reactive({
  name: "",
  description: "",
  entrypoint: "handle",
  status: "active",
  timeout_seconds: 60,
  max_writes: 100,
  source: DEFAULT_SOURCE,
});

const triggers = ref([
  { resource_type: "attribute", action: "created", filters: {} },
]);

function addTrigger() {
  triggers.value.push({
    resource_type: "attribute",
    action: "created",
    filters: {},
  });
}
function removeTrigger(idx) {
  triggers.value.splice(idx, 1);
}

const apiError = ref(null);
const canSubmit = computed(
  () => script.name && script.source && triggers.value.length > 0,
);

async function submit() {
  apiError.value = null;
  const cleanTriggers = triggers.value.map((t) => ({
    resource_type: t.resource_type,
    action: t.action,
    filters: Object.keys(t.filters || {}).length ? t.filters : null,
  }));
  await reactorStore
    .create({ ...script, triggers: cleanTriggers })
    .then((response) => {
      toastsStore.push(`Reactor script "${response.name}" created.`, "success");
      router.push(`/tech-lab/reactor/${response.id}`);
    })
    .catch((err) => (apiError.value = err?.message || String(err)));
}

function cancel() {
  router.push("/tech-lab/reactor");
}
</script>

<template>
  <div class="card mx-auto" style="max-width: 920px">
    <div class="card-header border-bottom">
      <h4 class="mb-0">New Reactor Script</h4>
      <small class="text-muted">
        Reacts to a trigger and runs in an isolated worker. Writes go through
        the audit log.
      </small>
    </div>
    <div class="card-body">
      <div class="mb-3">
        <label class="form-label" for="r-name">Name</label>
        <input id="r-name" class="form-control" v-model="script.name" />
      </div>

      <div class="mb-3">
        <label class="form-label" for="r-desc">Description</label>
        <textarea
          id="r-desc"
          class="form-control"
          rows="2"
          v-model="script.description"
        />
      </div>

      <div class="mb-3">
        <label class="form-label">Triggers</label>
        <div
          v-for="(t, idx) in triggers"
          :key="idx"
          class="d-flex gap-2 align-items-center mb-2"
        >
          <select v-model="t.resource_type" class="form-select form-select-sm">
            <option v-for="r in RESOURCE_OPTIONS" :key="r" :value="r">
              {{ r }}
            </option>
          </select>
          <select v-model="t.action" class="form-select form-select-sm">
            <option v-for="a in ACTION_OPTIONS" :key="a" :value="a">
              {{ a }}
            </option>
          </select>
          <input
            class="form-control form-control-sm font-monospace"
            placeholder='filters (JSON, e.g. {"tag":"tlp:red"})'
            :value="JSON.stringify(t.filters || {})"
            @input="
              (e) => {
                try {
                  t.filters = JSON.parse(e.target.value || '{}');
                } catch {}
              }
            "
          />
          <button
            class="btn btn-outline-danger btn-sm"
            @click="removeTrigger(idx)"
            :disabled="triggers.length === 1"
          >
            ×
          </button>
        </div>
        <button class="btn btn-outline-secondary btn-sm" @click="addTrigger">
          + add trigger
        </button>
      </div>

      <div class="mb-3">
        <label class="form-label" for="r-source">Python source</label>
        <textarea
          id="r-source"
          class="form-control font-monospace"
          rows="14"
          v-model="script.source"
          spellcheck="false"
        />
      </div>

      <div class="row g-3 mb-3">
        <div class="col">
          <label class="form-label" for="r-entry">Entrypoint</label>
          <input
            id="r-entry"
            class="form-control"
            v-model="script.entrypoint"
          />
        </div>
        <div class="col">
          <label class="form-label" for="r-timeout">Timeout (s)</label>
          <input
            id="r-timeout"
            type="number"
            class="form-control"
            v-model.number="script.timeout_seconds"
            min="1"
            max="600"
          />
        </div>
        <div class="col">
          <label class="form-label" for="r-writes">Max writes / run</label>
          <input
            id="r-writes"
            type="number"
            class="form-control"
            v-model.number="script.max_writes"
            min="0"
          />
        </div>
      </div>

      <div class="mb-4">
        <div class="form-check form-switch">
          <input
            class="form-check-input"
            type="checkbox"
            role="switch"
            id="r-active"
            :checked="script.status === 'active'"
            @change="
              script.status = $event.target.checked ? 'active' : 'paused'
            "
          />
          <label class="form-check-label" for="r-active">Active</label>
        </div>
      </div>

      <div v-if="apiError" class="alert alert-danger">{{ apiError }}</div>

      <div class="d-flex justify-content-end gap-2">
        <button class="btn btn-outline-secondary" @click="cancel">
          Cancel
        </button>
        <button
          class="btn btn-primary"
          :disabled="!canSubmit || reactorStore.status.creating"
          @click="submit"
        >
          {{ reactorStore.status.creating ? "Creating…" : "Create" }}
        </button>
      </div>
    </div>
  </div>
</template>
