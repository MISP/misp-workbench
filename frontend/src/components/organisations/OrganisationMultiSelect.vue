<script setup>
import { ref, watch, onMounted, onBeforeUnmount, nextTick } from "vue";
import TomSelect from "tom-select";
import { fetchWrapper } from "@/helpers/fetch-wrapper";

const baseUrl = `${import.meta.env.VITE_API_URL}/organisations`;

const props = defineProps({
  selected: { type: Array, default: () => [] },
});

const emit = defineEmits(["update:selected"]);

const selectElement = ref(null);
let tomselect = null;
let _updatingFromProp = false;

function initTomSelect() {
  if (!selectElement.value) return;

  if (tomselect) {
    tomselect.destroy();
    tomselect = null;
  }

  tomselect = new TomSelect(selectElement.value, {
    create: false,
    placeholder: "Click to add an organisation…",
    valueField: "name",
    labelField: "name",
    searchField: "name",
    preload: true,
    items: [...props.selected],
    plugins: { remove_button: { title: "Remove" } },

    load(_query, callback) {
      fetchWrapper
        .get(baseUrl)
        .then((orgs) => callback(orgs.map((o) => ({ name: o.name }))))
        .catch(() => callback());
    },

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
</script>

<template>
  <select ref="selectElement" multiple></select>
</template>
