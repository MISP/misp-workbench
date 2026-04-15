<script setup>
import { ref, watch, onMounted, onBeforeUnmount, nextTick } from "vue";
import TomSelect from "tom-select";
import { useGalaxiesStore } from "@/stores";

const props = defineProps({
  modelValue: { type: String, default: "" },
});

const emit = defineEmits(["update:modelValue"]);

const galaxiesStore = useGalaxiesStore();

const selectElement = ref(null);
let tomselect = null;
let _updatingFromProp = false;

function parseTokens(raw) {
  if (!raw) return [];
  return raw
    .replace(/\n/g, ",")
    .split(",")
    .map((t) => t.trim())
    .filter(Boolean);
}

function emitSelected() {
  if (!tomselect || _updatingFromProp) return;
  const items = Array.isArray(tomselect.items)
    ? tomselect.items
    : [tomselect.items].filter(Boolean);
  emit("update:modelValue", items.join(", "));
}

function formatPattern(p) {
  return {
    external_id: p.external_id,
    value: p.value,
    label: `${p.external_id} - ${p.value}`,
    description: p.description,
  };
}

function initTomSelect() {
  if (!selectElement.value) return;

  if (tomselect) {
    tomselect.destroy();
    tomselect = null;
  }

  tomselect = new TomSelect(selectElement.value, {
    create: false,
    placeholder: "Search MITRE ATT&CK technique (e.g. T1391)…",
    valueField: "external_id",
    labelField: "label",
    searchField: ["external_id", "value", "label"],
    preload: "focus",
    maxOptions: 500,
    options: parseTokens(props.modelValue).map((code) => ({
      external_id: code,
      value: "",
      label: code,
    })),
    items: parseTokens(props.modelValue),

    load(query, callback) {
      galaxiesStore
        .getMitreAttackPatterns(query)
        .then((response) => {
          const list = Array.isArray(response) ? response : [];
          callback(list.map(formatPattern));
        })
        .catch(() => callback());
    },

    plugins: { remove_button: { title: "Remove this technique" } },

    render: {
      option(data, escape) {
        const desc = data.description
          ? `<div class="text-muted small text-truncate">${escape(data.description)}</div>`
          : "";
        return `
          <div>
            <div><code>${escape(data.external_id)}</code> ${escape(data.value || "")}</div>
            ${desc}
          </div>`;
      },
      item(data, escape) {
        const title = data.value
          ? `${escape(data.external_id)} - ${escape(data.value)}`
          : escape(data.external_id);
        return `<span class="badge bg-secondary-subtle text-body mx-1" title="${title}">
            ${data.value ? " " + escape(data.value) : escape(data.external_id)}
          </span>`;
      },
    },

    onChange() {
      emitSelected();
    },
  });
}

onMounted(() => nextTick(initTomSelect));

onBeforeUnmount(() => {
  if (tomselect) {
    tomselect.destroy();
    tomselect = null;
  }
});

watch(
  () => props.modelValue,
  (newVal) => {
    if (!tomselect) return;
    const codes = parseTokens(newVal);
    const current = Array.isArray(tomselect.items) ? tomselect.items : [];
    if (
      codes.length === current.length &&
      codes.every((c, i) => c === current[i])
    ) {
      return;
    }
    _updatingFromProp = true;
    for (const code of codes) {
      if (!tomselect.options[code]) {
        tomselect.addOption({ external_id: code, value: "", label: code });
      }
    }
    tomselect.setValue(codes, true);
    _updatingFromProp = false;
  },
);
</script>

<style>
.ts-wrapper.multi .ts-control {
  max-height: 8.5rem;
  overflow-y: auto;
}
</style>

<template>
  <select ref="selectElement" multiple></select>
</template>
