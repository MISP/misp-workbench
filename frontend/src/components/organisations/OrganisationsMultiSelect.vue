<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick } from "vue";
import TomSelect from "tom-select";

const props = defineProps({
  selectedOrgs: { type: Array, default: () => [] },
});

const emit = defineEmits(["update:selectedOrgs"]);

const selectElement = ref(null);
let tomselect = null;

function emitSelected() {
  if (!tomselect) return;
  // tomselect.items is array of selected values (valueField = name)
  const items = Array.isArray(tomselect.items)
    ? tomselect.items
    : [tomselect.items].filter(Boolean);
  const selected = items.map((name) => {
    // tomselect.options keyed by valueField (name)
    const opt = tomselect.options && tomselect.options[name];
    if (opt) return opt.value;
    return name;
  });
  emit("update:selectedOrgs", selected);
}

function initTomSelect() {
  if (!selectElement.value) return;

  // destroy old instance if exists
  if (tomselect) {
    tomselect.destroy();
    tomselect = null;
  }

  tomselect = new TomSelect(selectElement.value, {
    create: true,
    placeholder: "Click to add an organisation...",
    items: props.selectedOrgs.map((org) => org),
    plugins: ["remove_button"],
    onItemRemove() {
      emitSelected();
    },
    onItemAdd() {
      emitSelected();
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
</script>

<template>
  <select ref="selectElement" multiple></select>
</template>
