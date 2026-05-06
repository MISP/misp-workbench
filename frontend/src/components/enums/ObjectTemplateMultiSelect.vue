<script setup>
import { ref, watch, onMounted, onBeforeUnmount, nextTick } from "vue";
import { storeToRefs } from "pinia";
import TomSelect from "tom-select";
import { useObjectsStore } from "@/stores";

const props = defineProps({
  selected: { type: Array, default: () => [] },
});
const emit = defineEmits(["update:selected"]);

const objectsStore = useObjectsStore();
const { objectTemplates } = storeToRefs(objectsStore);

const selectElement = ref(null);
let tomselect = null;
let _updatingFromProp = false;

function buildOptions() {
  const seen = new Set();
  return (objectTemplates.value || [])
    .map((t) => t.name)
    .filter((n) => n && !seen.has(n) && seen.add(n))
    .map((n) => ({ value: n, text: n }));
}

function initTomSelect() {
  if (!selectElement.value) return;
  if (tomselect) {
    tomselect.destroy();
    tomselect = null;
  }
  tomselect = new TomSelect(selectElement.value, {
    create: false,
    placeholder: "Click to add an object template…",
    valueField: "value",
    labelField: "text",
    searchField: "text",
    options: buildOptions(),
    items: [...props.selected],
    plugins: { remove_button: { title: "Remove" } },
    onChange() {
      if (_updatingFromProp) return;
      emit("update:selected", tomselect ? [...tomselect.items] : []);
    },
  });
}

onMounted(() => {
  if (!objectTemplates.value || objectTemplates.value.length === 0) {
    objectsStore.getObjectTemplates();
  }
  nextTick(initTomSelect);
});

onBeforeUnmount(() => {
  if (tomselect) {
    tomselect.destroy();
    tomselect = null;
  }
});

watch(
  () => props.selected,
  (newVal) => {
    if (!tomselect) return;
    _updatingFromProp = true;
    tomselect.setValue(newVal, true);
    _updatingFromProp = false;
  },
  { deep: true },
);

watch(
  objectTemplates,
  () => {
    if (!tomselect) return;
    tomselect.clearOptions();
    tomselect.addOptions(buildOptions());
    tomselect.refreshOptions(false);
  },
  { deep: true },
);
</script>

<template>
  <select ref="selectElement" multiple></select>
</template>
