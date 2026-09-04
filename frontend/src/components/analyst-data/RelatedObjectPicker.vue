<script setup>
import { ref, watch, onMounted, onBeforeUnmount, nextTick } from "vue";
import TomSelect from "tom-select";
import { useEventsStore, useAttributesStore, useObjectsStore } from "@/stores";

/**
 * Searches for the record an analyst relationship points at: an event, an
 * attribute or an object. The search is remote, so this works on instances
 * with more records than a dropdown could hold.
 *
 * The `<select>` is created imperatively into a host div rather than written
 * in the template. TomSelect hides the original element and wraps it, moving
 * it out of the position Vue recorded, so anything that made Vue re-patch this
 * subtree threw "Child to insert before is not a child of this node" and then
 * "el is null". Building the element ourselves keeps every node TomSelect
 * touches outside Vue's diffing, which lets the control be rebuilt safely when
 * the target type changes.
 */
const props = defineProps({
  modelValue: { type: String, default: "" },
  objectType: { type: String, default: "Event" },
});

const emit = defineEmits(["update:modelValue"]);

const eventsStore = useEventsStore();
const attributesStore = useAttributesStore();
const objectsStore = useObjectsStore();

const host = ref(null);
let tomselect = null;

// How each target type is searched, and how a hit is labelled. Kept together
// so adding a type later is one entry rather than branches in three places.
const sources = {
  Event: {
    placeholder: "Search events by info or uuid…",
    search: (query) => eventsStore.searchLookup({ query, page: 1, size: 25 }),
    format: (source) => ({
      uuid: source.uuid,
      primary: source.info || "(no info)",
      secondary: source.uuid,
    }),
  },
  Attribute: {
    placeholder: "Search attributes by value…",
    search: (query) =>
      attributesStore.searchLookup({ query, page: 1, size: 25 }),
    format: (source) => ({
      uuid: source.uuid,
      primary: source.value ?? source.uuid,
      secondary: [source.type, source.category].filter(Boolean).join(" · "),
    }),
  },
  Object: {
    placeholder: "Search objects by name or comment…",
    search: (query) => objectsStore.searchLookup({ query, page: 1, size: 25 }),
    format: (source) => ({
      uuid: source.uuid,
      primary: source.name ?? source.uuid,
      secondary: source.comment || source.description || source.uuid,
    }),
  },
};

function currentSource() {
  return sources[props.objectType] ?? sources.Event;
}

function destroy() {
  if (tomselect) {
    tomselect.destroy();
    tomselect = null;
  }
  // destroy() restores the original element rather than removing it, and the
  // host is ours to empty
  if (host.value) host.value.replaceChildren();
}

function initTomSelect() {
  if (!host.value) return;
  destroy();

  const source = currentSource();
  const element = document.createElement("select");
  host.value.appendChild(element);

  tomselect = new TomSelect(element, {
    create: false,
    maxItems: 1,
    placeholder: source.placeholder,
    valueField: "uuid",
    labelField: "primary",
    searchField: ["primary", "secondary", "uuid"],
    preload: "focus",
    maxOptions: 50,
    // The API does the matching, so tom-select must not filter the results
    // again -- a uuid query never matches the label it renders.
    shouldLoad: () => true,
    load(query, callback) {
      // The search endpoints match nothing on an empty query, so a wildcard
      // lists the most recent records when the picker is first opened.
      currentSource()
        .search(query?.trim() ? query : "*")
        .then((response) =>
          callback(
            (response?.results ?? []).map((hit) =>
              currentSource().format(hit._source ?? hit),
            ),
          ),
        )
        .catch(() => callback());
    },
    render: {
      option(data, escape) {
        return `
          <div>
            <div>${escape(data.primary ?? "")}</div>
            <div class="text-muted small">${escape(data.secondary ?? "")}</div>
          </div>`;
      },
      item(data, escape) {
        return `<div>${escape(data.primary ?? data.uuid)}</div>`;
      },
    },
    onChange(value) {
      emit("update:modelValue", value ?? "");
      // same reason as RelationshipTypeSelect: do not leave a long list open
      // over whatever follows
      tomselect?.close();
      tomselect?.blur();
    },
  });
}

/**
 * Show what is currently targeted when editing an existing relationship.
 *
 * Only the uuid is stored, so the record is looked up to get a readable
 * label. All three lookups return rather than storing, so this does not
 * disturb a list the page is already showing.
 */
async function preselect() {
  const uuid = props.modelValue;
  if (!uuid || !tomselect) return;

  const source = currentSource();

  // Selectable straight away, labelled with the uuid until the lookup lands.
  tomselect.addOption({ uuid, primary: uuid, secondary: "" });
  tomselect.setValue(uuid, true);

  try {
    const response = await source.search(uuid);
    const hit = (response?.results ?? [])
      .map((h) => h._source ?? h)
      .find((h) => h.uuid === uuid);
    if (!hit || !tomselect) return;

    tomselect.updateOption(uuid, source.format(hit));
    tomselect.setValue(uuid, true);
  } catch {
    // leave the uuid showing: the relationship is still valid and editable
  }
}

function build() {
  initTomSelect();
  preselect();
}

// Rebuilt on a type change. Safe now that Vue does not own these nodes, and it
// avoids re-pointing a live control, which fought TomSelect's option cache and
// its one-shot focus preload.
watch(
  () => props.objectType,
  () => nextTick(build),
);

onMounted(() => nextTick(build));

onBeforeUnmount(destroy);
</script>

<template>
  <!-- TomSelect builds its control inside here; the contents are deliberately
       not rendered by Vue -->
  <div ref="host"></div>
</template>
