<script setup>
import { ref, watch, onMounted, onBeforeUnmount, nextTick } from "vue";
import TomSelect from "tom-select";
import { ATTRIBUTE_TYPES, ATTRIBUTE_CATEGORIES } from "@/helpers/constants";

const props = defineProps({
  selected: { type: Array, default: () => [] },
  category: { type: String, default: null },
});

const emit = defineEmits(["update:selected"]);

const selectElement = ref(null);
let tomselect = null;
let _updatingFromProp = false;

function resolveTypes(category) {
  if (category && ATTRIBUTE_CATEGORIES[category] !== undefined) {
    return ATTRIBUTE_CATEGORIES[category].types;
  }
  return ATTRIBUTE_TYPES;
}

function buildOptions(category) {
  return resolveTypes(category).map((t) => ({ value: t, text: t }));
}

function initTomSelect() {
  if (!selectElement.value) return;

  if (tomselect) {
    tomselect.destroy();
    tomselect = null;
  }

  tomselect = new TomSelect(selectElement.value, {
    create: false,
    placeholder: "Click to add an attribute type…",
    valueField: "value",
    labelField: "text",
    searchField: "text",
    options: buildOptions(props.category),
    items: [...props.selected],
    plugins: { remove_button: { title: "Remove" } },
    onChange() {
      if (_updatingFromProp) return;
      emit("update:selected", tomselect ? [...tomselect.items] : []);
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
  () => props.category,
  (newCategory) => {
    if (!tomselect) return;
    const newOptions = buildOptions(newCategory);
    tomselect.clearOptions();
    tomselect.addOptions(newOptions);
    tomselect.clear(true);
    emit("update:selected", []);
  },
);
</script>

<template>
  <select ref="selectElement" multiple></select>
</template>
