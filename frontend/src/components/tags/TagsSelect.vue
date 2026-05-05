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
  readonly: { type: Boolean, default: false },
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
    value: tag.name,
    color: tagHelper.getContrastColor(tag.colour),
    backgroundColor: tag.colour,
  };
}

function defaultColourFor(name) {
  // Deterministic hex colour from the tag name so newly-created tags get a
  // stable preview before the backend assigns the canonical one.
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = (hash * 31 + name.charCodeAt(i)) | 0;
  }
  const hex = ((hash >>> 0) & 0xffffff).toString(16).padStart(6, "0");
  return `#${hex}`;
}

function initTomSelect() {
  if (!selectElement.value) return;

  // destroy old instance if exists
  if (tomselect) {
    tomselect.destroy();
    tomselect = null;
  }

  tomselect = new TomSelect(selectElement.value, {
    create: props.readonly
      ? false
      : (input) => {
          const name = input.trim();
          if (!name) return false;
          const colour = defaultColourFor(name);
          return {
            id: null,
            name,
            value: name,
            color: tagHelper.getContrastColor(colour),
            backgroundColor: colour,
          };
        },
    createFilter: (input) => input.trim().length > 0,
    placeholder: props.readonly ? "" : "Click to add a tag...",
    readOnly: props.readonly,
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
            ${escape(data.value)}
          </span>`;
      },
      item(data, escape) {
        return `
          <span class="badge mx-1 tag"
                style="display:block; color:${escape(data.color)}; background-color:${escape(data.backgroundColor)}"
                title="${escape(data.name)}">
            <span class="tag-label">${escape(data.value)}<span/>
          </span>`;
      },
    },

    onItemRemove(tag) {
      if (!props.persist || _updatingFromProp) return;

      const modelId = props.model?.uuid ?? props.model?.id;
      if (props.modelClass === "event") {
        eventsStore.untag(modelId, tag);
      } else if (props.modelClass === "attribute") {
        attributesStore.untag(modelId, tag);
      }
      emitSelected();
    },

    onItemAdd(tag) {
      if (!props.persist || _updatingFromProp) return;

      const modelId = props.model?.uuid ?? props.model?.id;
      if (props.modelClass === "event") {
        eventsStore.tag(modelId, tag);
      } else if (props.modelClass === "attribute") {
        attributesStore.tag(modelId, tag);
      }
      emitSelected();
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

.ts-wrapper.multi .ts-control {
  max-height: 8.5rem;
  overflow-y: auto;
}

.ts-wrapper.multi .ts-control > .item {
  max-width: 100%;
}

.ts-wrapper.multi .ts-control .tag {
  max-width: 100%;
  overflow-x: auto;
  white-space: nowrap;
}

.ts-wrapper.multi .ts-control .tag-label {
  display: inline-block;
  white-space: nowrap;
}
</style>

<template>
  <select ref="selectElement" multiple></select>
</template>
