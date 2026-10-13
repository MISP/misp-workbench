<script setup>
import { ref, computed } from "vue";
import { fetchWrapper } from "@/helpers";

// Runs the enabled enrichment modules that take the indicator's type, on
// demand, and lists what they return. Nothing is written to any event.
const props = defineProps({ indicator: { type: Object, required: true } });

const baseUrl = `${import.meta.env.VITE_API_URL}/modules`;
const modules = ref(null);
const results = ref([]);
const running = ref(false);
const error = ref(null);

const applicable = computed(() =>
  (modules.value || []).filter((m) =>
    (m.misp_attributes?.input || []).includes(props.indicator.type),
  ),
);

async function loadModules() {
  if (modules.value !== null) return;
  try {
    modules.value = await fetchWrapper.get(`${baseUrl}/?enabled=true`);
  } catch (e) {
    modules.value = [];
    error.value = e;
  }
}

function summarise(response) {
  const found = response?.results || {};
  const attributes = (found.Attribute || [])
    .filter((a) => String(a.value) !== props.indicator.value)
    .map((a) => `${a.type}: ${a.value}`);
  const objects = (found.Object || []).map(
    (o) => `${o.name} (${(o.Attribute || []).length} attributes)`,
  );
  return [...attributes, ...objects];
}

async function run() {
  await loadModules();
  running.value = true;
  results.value = [];
  const attribute = {
    uuid: props.indicator.uuid,
    type: props.indicator.type,
    value: props.indicator.value,
  };
  await Promise.all(
    applicable.value.map((m) =>
      fetchWrapper
        .post(`${baseUrl}/query`, {
          module: m.name,
          attribute,
          config: m.config,
        })
        .then((response) =>
          results.value.push({ module: m.name, items: summarise(response) }),
        )
        .catch((e) =>
          results.value.push({ module: m.name, items: [], error: `${e}` }),
        ),
    ),
  );
  running.value = false;
}

loadModules();
</script>

<template>
  <div class="small">
    <div class="d-flex align-items-center gap-2 mb-1">
      <strong>enrichment</strong>
      <button
        type="button"
        class="btn btn-outline-secondary btn-sm py-0"
        :disabled="running || !applicable.length"
        @click.stop="run"
      >
        {{ running ? "running…" : "run modules" }}
      </button>
      <span v-if="modules !== null && !applicable.length" class="text-muted"
        >No enabled module takes {{ indicator.type }}.</span
      >
      <span v-else-if="modules !== null" class="text-muted">{{
        applicable.map((m) => m.name).join(", ")
      }}</span>
    </div>
    <div v-if="error" class="text-danger">{{ error }}</div>
    <ul class="list-unstyled mb-0">
      <li v-for="r in results" :key="r.module">
        <span class="fw-semibold">{{ r.module }}</span
        >:
        <span v-if="r.error" class="text-danger">{{ r.error }}</span>
        <span v-else-if="!r.items.length" class="text-muted">nothing</span>
        <span v-else class="font-monospace text-break">{{
          r.items.slice(0, 10).join(" · ")
        }}</span>
        <span v-if="r.items.length > 10" class="text-muted">
          and {{ r.items.length - 10 }} more</span
        >
      </li>
    </ul>
  </div>
</template>
