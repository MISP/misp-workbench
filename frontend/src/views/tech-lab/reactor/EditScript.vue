<script setup>
import { ref, reactive, onMounted, computed } from "vue";
import { router } from "@/router";
import { useReactorStore, useToastsStore } from "@/stores";

const props = defineProps({ id: { type: [String, Number], required: true } });

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

const script = reactive({
  name: "",
  description: "",
  entrypoint: "handle",
  status: "active",
  timeout_seconds: 60,
  max_writes: 100,
  source: "",
});
const triggers = ref([]);
const apiError = ref(null);
const loaded = ref(false);

onMounted(async () => {
  const detail = await reactorStore.getById(props.id);
  Object.assign(script, {
    name: detail.name,
    description: detail.description,
    entrypoint: detail.entrypoint,
    status: detail.status,
    timeout_seconds: detail.timeout_seconds,
    max_writes: detail.max_writes,
  });
  triggers.value = (detail.triggers || []).map((t) => ({
    resource_type: t.resource_type,
    action: t.action,
    filters: t.filters || {},
  }));
  const sourceResp = await reactorStore.getSource(props.id);
  script.source = sourceResp.source;
  loaded.value = true;
});

const canSubmit = computed(
  () => loaded.value && script.name && triggers.value.length > 0,
);

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

async function submit() {
  apiError.value = null;
  const cleanTriggers = triggers.value.map((t) => ({
    resource_type: t.resource_type,
    action: t.action,
    filters: Object.keys(t.filters || {}).length ? t.filters : null,
  }));
  await reactorStore
    .update(props.id, { ...script, triggers: cleanTriggers })
    .then(() => {
      toastsStore.push(`Reactor script "${script.name}" updated.`, "success");
      router.push(`/tech-lab/reactor/${props.id}`);
    })
    .catch((err) => (apiError.value = err?.message || String(err)));
}

function cancel() {
  router.push(`/tech-lab/reactor/${props.id}`);
}
</script>

<template>
  <div class="card mx-auto" style="max-width: 920px" v-if="loaded">
    <div class="card-header border-bottom">
      <h4 class="mb-0">Edit Reactor Script</h4>
    </div>
    <div class="card-body">
      <div class="mb-3">
        <label class="form-label">Name</label>
        <input class="form-control" v-model="script.name" />
      </div>
      <div class="mb-3">
        <label class="form-label">Description</label>
        <textarea class="form-control" rows="2" v-model="script.description" />
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
          >
            ×
          </button>
        </div>
        <button class="btn btn-outline-secondary btn-sm" @click="addTrigger">
          + add trigger
        </button>
      </div>

      <div class="mb-3">
        <label class="form-label">Python source</label>
        <textarea
          class="form-control font-monospace"
          rows="14"
          v-model="script.source"
          spellcheck="false"
        />
      </div>

      <div class="row g-3 mb-3">
        <div class="col">
          <label class="form-label">Entrypoint</label>
          <input class="form-control" v-model="script.entrypoint" />
        </div>
        <div class="col">
          <label class="form-label">Timeout (s)</label>
          <input
            type="number"
            class="form-control"
            v-model.number="script.timeout_seconds"
          />
        </div>
        <div class="col">
          <label class="form-label">Max writes / run</label>
          <input
            type="number"
            class="form-control"
            v-model.number="script.max_writes"
          />
        </div>
      </div>

      <div class="mb-4 form-check form-switch">
        <input
          class="form-check-input"
          type="checkbox"
          role="switch"
          id="re-active"
          :checked="script.status === 'active'"
          @change="script.status = $event.target.checked ? 'active' : 'paused'"
        />
        <label class="form-check-label" for="re-active">Active</label>
      </div>

      <div v-if="apiError" class="alert alert-danger">{{ apiError }}</div>

      <div class="d-flex justify-content-end gap-2">
        <button class="btn btn-outline-secondary" @click="cancel">
          Cancel
        </button>
        <button
          class="btn btn-primary"
          :disabled="!canSubmit || reactorStore.status.updating"
          @click="submit"
        >
          {{ reactorStore.status.updating ? "Saving…" : "Save" }}
        </button>
      </div>
    </div>
  </div>
</template>
