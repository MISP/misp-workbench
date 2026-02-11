<script setup>
import { ref, watch, onMounted, onBeforeUnmount, nextTick } from "vue";
import TomSelect from "tom-select";
import { tagHelper } from "@/helpers";
import { useTagsStore, useAttributesStore, useEventsStore } from "@/stores";

const props = defineProps({
  modelClass: { type: String, required: true },
  model: { type: Object, required: false },
  selectedTags: { type: Array, default: () => [] },
  persist: { type: Boolean, default: true },
});

const emit = defineEmits(["update:selectedTags"]);

const tagsStore = useTagsStore();
const eventsStore = useEventsStore();
const attributesStore = useAttributesStore();

const selectElement = ref(null);
let tomselect = null;
let _updatingFromProp = false;

function emitSelected() {
  if (!tomselect) return;
  // tomselect.items is array of selected values (valueField = name)
  const items = Array.isArray(tomselect.items)
    ? tomselect.items
    : [tomselect.items].filter(Boolean);
  const selected = items.map((name) => {
    // tomselect.options keyed by valueField (name)
    const opt = tomselect.options && tomselect.options[name];
    if (opt) return opt.name;
    return name;
  });
  emit("update:selectedTags", selected);
}

function formatTag(tag) {
  return {
    id: tag.id,
    name: tag.name,
    color: tagHelper.getContrastColor(tag.colour),
    backgroundColor: tag.colour,
  };
}

function initTomSelect() {
  if (!selectElement.value) return;

  // destroy old instance if exists
  if (tomselect) {
    tomselect.destroy();
    tomselect = null;
  }

  tomselect = new TomSelect(selectElement.value, {
    create: false,
    placeholder: "Click to add a tag...",
    valueField: "name",
    labelField: "name",
    searchField: "name",
    preload: true,
    options: props.selectedTags.map(formatTag),
    items: props.selectedTags.map((tag) => tag.name),

    load(query, callback) {
      tagsStore
        .get({ filter: query, hidden: false })
        .then((response) => {
          callback(response.items.map(formatTag));
        })
        .catch(() => callback());
    },

    plugins: { remove_button: { title: "Remove this tag" } },

    render: {
      option(data, escape) {
        return `
          <span class="badge mx-1 tag"
                style="color:${escape(data.color)}; background-color:${escape(data.backgroundColor)}"
                title="${escape(data.name)}">
            ${escape(data.name)}
          </span>`;
      },
      item(data, escape) {
        return `
          <span class="badge mx-1 tag"
                style="display:block; color:${escape(data.color)}; background-color:${escape(data.backgroundColor)}"
                title="${escape(data.name)}">
            <span class="tag-label">${escape(data.name)}<span/>
          </span>`;
      },
    },

    onItemRemove(tag) {
      if (!props.persist) return;

      if (props.modelClass === "event") {
        eventsStore.untag(props.model.id, tag);
      } else if (props.modelClass === "attribute") {
        attributesStore.untag(props.model.id, tag);
      }
      // notify parent of change
      if (!_updatingFromProp) emitSelected();
    },

    onItemAdd(tag) {
      if (!props.persist) return;

      if (props.modelClass === "event") {
        eventsStore.tag(props.model.id, tag);
      } else if (props.modelClass === "attribute") {
        attributesStore.tag(props.model.id, tag);
      }
      // notify parent of change
      if (!_updatingFromProp) emitSelected();
    },
    onChange() {
      if (_updatingFromProp) return;
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

// if props.selectedTags changes while component is alive
watch(
  () => props.selectedTags,
  (newTags) => {
    if (tomselect) {
      _updatingFromProp = true;
      const names = newTags.map((tag) => tag.name);
      tomselect.clearOptions();
      tomselect.addOptions(newTags.map(formatTag));
      tomselect.setValue(names, true);
      // emit the normalized objects once update completes
      emitSelected();
      _updatingFromProp = false;
    }
  },
  { deep: true },
);
</script>

<style>
[data-bs-theme="dark"] .ts-control,
[data-bs-theme="dark"] .ts-control input {
  color: #fff !important;
  background-color: transparent !important;
}
</style>

<template>
  <select ref="selectElement" multiple></select>
</template>
