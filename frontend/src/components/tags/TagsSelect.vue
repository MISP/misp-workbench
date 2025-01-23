<script setup>
import { ref, onMounted, nextTick } from "vue";
import { tagHelper } from "@/helpers";
import TomSelect from "tom-select";
import { useTagsStore, useAttributesStore, useEventsStore } from "@/stores";

const props = defineProps({
  modelClass: {
    type: String,
    required: true,
  },
  model: {
    type: Object,
    required: true,
  },
  selectedTags: {
    type: Array,
    default: () => [],
  },
});
const tagsStore = useTagsStore();
const eventsStore = useEventsStore();
const attributesStore = useAttributesStore();

const selectElement = ref(null);

onMounted(() => {
  let initialising = true;
  new TomSelect(selectElement.value, {
    create: false,
    placeholder: "Click to add a tag...",
    valueField: "name",
    labelField: "name",
    searchField: "name",
    preload: true,
    load: function (query, callback) {
      // add already selected tags to the list first
      const tags = [];
      for (let i = 0; i < props.selectedTags.length; i++) {
        tags.push(
          {
            id: props.selectedTags[i].id,
            name: props.selectedTags[i].name,
            color: tagHelper.getContrastColor(props.selectedTags[i].colour),
            backgroundColor: props.selectedTags[i].colour,
          },
          false,
        );
      }

      // add tags from the database to the list
      tagsStore
        .get({ filter: query, hidden: false })
        .then((response) => {
          for (let i = 0; i < response.items.length; i++) {
            tags.push({
              id: response.items[i].id,
              name: response.items[i].name,
              color: tagHelper.getContrastColor(response.items[i].colour),
              backgroundColor: response.items[i].colour,
            });
          }
          callback(tags);
        })
        .catch(() => {
          callback();
        });
    },
    items: props.selectedTags.map((tag) => tag.name),
    plugins: {
      remove_button: {
        title: "Remove this tag",
      },
    },
    render: {
      option: function (data, escape) {
        return (
          '<span class="badge mx-1 tag" style="color: ' +
          escape(data.color) +
          "; background-color: " +
          escape(data.backgroundColor) +
          ';" title="' +
          escape(data.name) +
          '">' +
          escape(data.name) +
          "</span>"
        );
      },
      item: function (data, escape) {
        return (
          '<span class="badge mx-1 tag" style="display:block; color: ' +
          escape(data.color) +
          "; background-color: " +
          escape(data.backgroundColor) +
          ';" title="' +
          escape(data.name) +
          '"><span class="tag-label">' +
          escape(data.name) +
          "<span/></span>"
        );
      },
    },
    onLoad() {
      const tags = props.selectedTags
        ? props.selectedTags.map((tag) => tag.name)
        : [];
      selectElement.value.tomselect.setValue(tags, true);
      initialising = false;
    },
    onItemRemove: function (tag) {
      if (props.modelClass == "event") {
        eventsStore.untag(props.model.id, tag);
        return;
      }
      if (props.modelClass == "attribute") {
        attributesStore.untag(props.model.id, tag);
        return;
      }
    },
    onItemAdd: function (tag, item) {
      // ignore when adding items programmatically on initialisation
      if (initialising) {
        return;
      }
      if (props.modelClass == "event") {
        eventsStore.tag(props.model.id, tag);
        return;
      }
      if (props.modelClass == "attribute") {
        attributesStore.tag(props.model.id, tag);
        return;
      }
    },
  });
});
</script>

<style></style>

<template>
  <select ref="selectElement" multiple></select>
</template>
