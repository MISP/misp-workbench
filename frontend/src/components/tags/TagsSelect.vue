<script setup>
import { ref, watch, onMounted, onBeforeUnmount, nextTick } from "vue";
import TomSelect from "tom-select";
import { tagHelper } from "@/helpers";
import { useTagsStore, useAttributesStore, useEventsStore } from "@/stores";

const props = defineProps({
  modelClass: { type: String, required: true },
  model: { type: Object, required: true },
  selectedTags: { type: Array, default: () => [] },
});

const tagsStore = useTagsStore();
const eventsStore = useEventsStore();
const attributesStore = useAttributesStore();

const selectElement = ref(null);
let tomselect = null;

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
      if (props.modelClass === "event") {
        eventsStore.untag(props.model.id, tag);
      } else if (props.modelClass === "attribute") {
        attributesStore.untag(props.model.id, tag);
      }
    },

    onItemAdd(tag) {
      if (props.modelClass === "event") {
        eventsStore.tag(props.model.id, tag);
      } else if (props.modelClass === "attribute") {
        attributesStore.tag(props.model.id, tag);
      }
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
      const names = newTags.map((tag) => tag.name);
      tomselect.clearOptions();
      tomselect.addOptions(newTags.map(formatTag));
      tomselect.setValue(names, true);
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
