<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick, watch } from "vue";
import TomSelect from "tom-select";
import { useAnalystDataStore } from "@/stores";

// The MISP relationship vocabulary, served from the misp-objects submodule.
// `create` is on because MISP allows a free-form relationship type, and one
// arriving over sync may not be in the shipped list.
const props = defineProps({
  modelValue: { type: String, default: "" },
});

const emit = defineEmits(["update:modelValue"]);

const analystDataStore = useAnalystDataStore();
const selectElement = ref(null);
let tomselect = null;

async function initTomSelect() {
  if (!selectElement.value) return;

  const types = (await analystDataStore.getRelationshipTypes()) ?? [];

  // the modal body can unmount while the vocabulary is in flight
  if (!selectElement.value) return;

  tomselect = new TomSelect(selectElement.value, {
    create: true,
    maxItems: 1,
    placeholder: "Search or type a relationship…",
    valueField: "name",
    labelField: "name",
    searchField: ["name", "description"],
    maxOptions: 100,
    options: types,
    items: props.modelValue ? [props.modelValue] : [],
    render: {
      option(data, escape) {
        const description = data.description
          ? `<div class="text-muted small text-truncate">${escape(data.description)}</div>`
          : "";
        return `<div><div>${escape(data.name)}</div>${description}</div>`;
      },
      option_create(data, escape) {
        return `<div class="create">Use <strong>${escape(data.input)}</strong></div>`;
      },
    },
    onChange(value) {
      emit("update:modelValue", value ?? "");
    },
  });

  if (props.modelValue && !tomselect.options[props.modelValue]) {
    tomselect.addOption({ name: props.modelValue, description: null });
    tomselect.setValue(props.modelValue, true);
  }
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
  (value) => {
    if (!tomselect || tomselect.getValue() === value) return;
    if (value && !tomselect.options[value]) {
      tomselect.addOption({ name: value, description: null });
    }
    tomselect.setValue(value ?? "", true);
  },
);
</script>

<template>
  <select ref="selectElement"></select>
</template>
