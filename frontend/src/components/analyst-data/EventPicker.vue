<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick } from "vue";
import TomSelect from "tom-select";
import { useEventsStore } from "@/stores";

// Picks the event a relationship points at. Searches the event index remotely,
// so it works on instances with more events than a dropdown could hold.
const props = defineProps({
  modelValue: { type: String, default: "" },
});

const emit = defineEmits(["update:modelValue"]);

const eventsStore = useEventsStore();
const selectElement = ref(null);
let tomselect = null;

function formatEvent(hit) {
  const source = hit._source ?? hit;
  return {
    uuid: source.uuid,
    info: source.info ?? "",
    label: source.info ? `${source.info}` : source.uuid,
  };
}

/**
 * Show the currently related event when editing an existing relationship.
 *
 * The uuid alone is all the form holds, so the event is looked up to get a
 * readable label. `summary` returns rather than storing, so this does not
 * disturb the event the page is already showing.
 */
async function preselect() {
  const uuid = props.modelValue;
  if (!uuid || !tomselect) return;

  // Selectable straight away, labelled with the uuid until the lookup lands.
  tomselect.addOption({ uuid, info: "", label: uuid });
  tomselect.setValue(uuid, true);

  try {
    const event = await eventsStore.summary(uuid);
    if (!tomselect || !event?.uuid) return;

    tomselect.updateOption(uuid, formatEvent(event));
    tomselect.setValue(uuid, true);
  } catch {
    // leave the uuid showing: the relationship is still valid and editable
  }
}

function initTomSelect() {
  if (!selectElement.value) return;

  tomselect = new TomSelect(selectElement.value, {
    create: false,
    maxItems: 1,
    placeholder: "Search events by info or uuid…",
    valueField: "uuid",
    labelField: "label",
    searchField: ["info", "uuid"],
    preload: "focus",
    maxOptions: 50,
    // The API does the matching, so tom-select must not filter the results
    // again -- a uuid query never matches the label it renders.
    shouldLoad: () => true,
    load(query, callback) {
      // The search endpoint matches nothing on an empty query, which left the
      // dropdown blank when it was first opened. A wildcard lists the most
      // recent events instead, which is what a picker should offer up front.
      const search = query?.trim() ? query : "*";

      eventsStore
        .searchLookup({ query: search, page: 1, size: 25 })
        .then((response) => {
          callback((response?.results ?? []).map(formatEvent));
        })
        .catch(() => callback());
    },
    render: {
      option(data, escape) {
        return `
          <div>
            <div>${escape(data.info || "(no info)")}</div>
            <div class="text-muted small"><code>${escape(data.uuid)}</code></div>
          </div>`;
      },
      item(data, escape) {
        return `<div>${escape(data.info || data.uuid)}</div>`;
      },
    },
    onChange(value) {
      emit("update:modelValue", value ?? "");
    },
  });
}

onMounted(() =>
  nextTick(() => {
    initTomSelect();
    preselect();
  }),
);

onBeforeUnmount(() => {
  if (tomselect) {
    tomselect.destroy();
    tomselect = null;
  }
});
</script>

<template>
  <select ref="selectElement"></select>
</template>
