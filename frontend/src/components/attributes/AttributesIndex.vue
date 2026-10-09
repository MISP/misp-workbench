<script setup>
import { ref, onMounted } from "vue";
import { storeToRefs } from "pinia";
import { useAttributesStore, useAnalystDataStore } from "@/stores";
import TagsSelect from "@/components/tags/TagsSelect.vue";
import Paginate from "vuejs-paginate-next";
import AddAttributeModal from "@/components/attributes/AddAttributeModal.vue";
import AttributeActions from "@/components/attributes/AttributeActions.vue";
import AnalystDataIndex from "@/components/analyst-data/AnalystDataIndex.vue";
import CopyToClipboard from "@/components/misc/CopyToClipboard.vue";
import Timestamp from "@/components/misc/Timestamp.vue";
import { Modal } from "bootstrap";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import {
  faSpinner,
  faCommentDots,
  faShield,
  faTriangleExclamation,
} from "@fortawesome/free-solid-svg-icons";

const props = defineProps(["event_uuid", "page_size"]);

const emit = defineEmits([
  "attribute-created",
  "object-created",
  "attribute-enriched",
]);

const attributesStore = useAttributesStore();
const { page_count, attributes, status } = storeToRefs(attributesStore);

const addAttributeModal = ref(null);

onMounted(() => {
  addAttributeModal.value = new Modal(
    document.getElementById("addAttributeModal"),
  );
});

function openAddAttributeModal() {
  addAttributeModal.value.show();
}

function onPageChange(page) {
  attributesStore.get({
    page: page,
    size: props.page_size,
    event_uuid: props.event_uuid,
    deleted: false,
  });
}
onPageChange(1);

function handleAttributesUpdated() {
  // TODO FIXME: resets the page to 1 and reloads the attributes, not the best way to do this, reload current page
  onPageChange(1);
}

function handleObjectCreated(object) {
  emit("object-created", object);
}

// Toggled in place, optimistically: the switch flips at once and flips back if
// the PATCH fails, rather than reloading the page of attributes.
const pendingToIds = ref(new Set());
const toIdsError = ref(null);

async function toggleToIds(attribute) {
  if (pendingToIds.value.has(attribute.uuid)) return;

  const previous = attribute.to_ids;
  attribute.to_ids = !previous;
  toIdsError.value = null;
  pendingToIds.value = new Set(pendingToIds.value).add(attribute.uuid);

  try {
    await attributesStore.setToIds(attribute.uuid, attribute.to_ids);
  } catch (error) {
    attribute.to_ids = previous;
    toIdsError.value = `Could not update the IDS flag of ${attribute.value}: ${error}`;
  } finally {
    const done = new Set(pendingToIds.value);
    done.delete(attribute.uuid);
    pendingToIds.value = done;
  }
}

// Analyst data is loaded per attribute only when its row is expanded: mounting
// one index per row would fire a request for every attribute on the page.
const analystDataStore = useAnalystDataStore();
const expandedAnalystData = ref(new Set());
const loadingAnalystData = ref(new Set());

// One request badges every row, so the counts are known without expanding
// anything. Refreshed whenever a panel reports a change.
function loadAnalystDataCounts() {
  if (!props.event_uuid) return;
  analystDataStore.getCountsByEventUuid(props.event_uuid);
}

loadAnalystDataCounts();

function analystDataCount(uuid) {
  return analystDataStore.countFromEvent(uuid);
}

/**
 * Fetch before expanding, and show the wait in the button.
 *
 * Inserting the row first meant it appeared at the height of a spinner and
 * then grew when the data arrived, which moved everything around it twice --
 * the row visibly bounced. Loading first means the row is inserted once, at
 * its final height.
 */
async function toggleAnalystData(uuid) {
  const next = new Set(expandedAnalystData.value);

  if (next.has(uuid)) {
    next.delete(uuid);
    expandedAnalystData.value = next;
    return;
  }

  if (!analystDataStore.hasThreadsFor(uuid)) {
    const loading = new Set(loadingAnalystData.value);
    loading.add(uuid);
    loadingAnalystData.value = loading;

    try {
      await analystDataStore.getByObjectUuid(uuid, "Attribute");
    } finally {
      const done = new Set(loadingAnalystData.value);
      done.delete(uuid);
      loadingAnalystData.value = done;
    }
  }

  expandedAnalystData.value = new Set(expandedAnalystData.value).add(uuid);
}
</script>

<style scoped>
.table {
  table-layout: fixed;
  /* below this the columns would be squeezed past readability, so the
     container scrolls instead */
  min-width: 42rem;
}

/*
 * The action toolbar is a fixed ~195px wide (plus the analyst data toggle), but
 * `table-layout: fixed` was splitting what the percentage columns left over
 * between four columns, giving actions ~100px at 768px and still only ~167px at
 * 1200px. The toolbar overflowed its cell and drew over the timestamp column.
 * An explicit width is authoritative under fixed layout, so the column now
 * reserves what its content needs.
 */
.actions-col {
  width: 16rem;
}

/*
 * A small superscript count overlapping the icon, like a notification badge.
 *
 * Selected via `.btn >` deliberately: Bootstrap's `.btn .badge` sets
 * position: relative and would otherwise win, putting the badge in flow and
 * widening the button.
 */
.btn > .analyst-count {
  position: absolute;
  top: 0;
  right: 0;
  transform: translate(35%, -35%);
  font-size: 0.65em;
  padding: 0.2em 0.4em;
  line-height: 1;
}

/*
 * type and timestamp are sized to their content so the leftover goes to value,
 * which is the column worth reading and was being truncated to "185.2..." once
 * actions took a fixed share.
 */
.type-col {
  width: 6rem;
}

.timestamp-col {
  width: 12rem;
  white-space: nowrap;
}

.ids-col {
  width: 3.5rem;
}

/* Attributes flagged for IDS export get a red bar down their left edge, so
   they stand out while scanning the list without reading the IDS column. */
tr.to-ids > td:first-child {
  box-shadow: inset 3px 0 0 var(--bs-danger);
}

.ids-toggle {
  line-height: 1;
}

.ids-toggle:not(.is-ids) {
  color: var(--bs-secondary-color);
  opacity: 0.6;
}

.ids-toggle:not(.is-ids):hover,
.ids-toggle:not(.is-ids):focus-visible {
  opacity: 1;
}

.value {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
  box-sizing: border-box;
}
</style>

<template>
  <div class="table-responsive">
    <div v-if="status.error" class="text-danger">
      Error loading attributes: {{ status.error }}
    </div>
    <div
      v-if="toIdsError"
      class="alert alert-danger alert-dismissible py-2 small"
      role="alert"
    >
      {{ toIdsError }}
      <button
        type="button"
        class="btn-close"
        aria-label="Close"
        @click="toIdsError = null"
      ></button>
    </div>
    <table class="table table-striped">
      <thead>
        <tr>
          <th scope="col">value</th>
          <th
            scope="col"
            class="ids-col text-center"
            title="Flagged for intrusion detection systems (to_ids)"
          >
            IDS
          </th>
          <th scope="col" class="type-col">type</th>
          <th style="width: 22%" scope="col" class="d-none d-sm-table-cell">
            tags
          </th>
          <!-- timestamp is the first column to go: below lg there is not room
               for it and the action toolbar side by side -->
          <th scope="col" class="timestamp-col d-none d-lg-table-cell">
            timestamp
          </th>
          <th scope="col" class="actions-col text-end">actions</th>
        </tr>
      </thead>
      <tbody>
        <template :key="attribute.uuid" v-for="attribute in attributes.items">
          <tr :class="{ 'to-ids': attribute.to_ids }">
            <td class="value">
              <CopyToClipboard :value="attribute.value" />
              {{ attribute.value }}
              <span
                v-if="attribute.warninglist_hits?.length"
                class="badge bg-warning-subtle text-warning-emphasis ms-1"
                :title="`On warninglists: ${attribute.warninglist_hits.join(', ')}`"
              >
                <FontAwesomeIcon :icon="faTriangleExclamation" />
                warninglist
              </span>
            </td>
            <td class="ids-col text-center">
              <button
                type="button"
                class="btn btn-sm ids-toggle"
                :class="
                  attribute.to_ids
                    ? 'is-ids bg-danger-subtle text-danger border-danger-subtle'
                    : 'border-0'
                "
                :aria-pressed="attribute.to_ids ? 'true' : 'false'"
                :disabled="pendingToIds.has(attribute.uuid)"
                :title="
                  attribute.to_ids
                    ? 'Flagged for IDS - click to unflag'
                    : 'Not flagged for IDS - click to flag'
                "
                @click="toggleToIds(attribute)"
              >
                <span
                  v-if="pendingToIds.has(attribute.uuid)"
                  class="spinner-border spinner-border-sm"
                  role="status"
                  aria-hidden="true"
                ></span>
                <FontAwesomeIcon v-else :icon="faShield" />
                <span class="visually-hidden">
                  {{ attribute.to_ids ? "Unflag for IDS" : "Flag for IDS" }}
                </span>
              </button>
            </td>
            <td>{{ attribute.type }}</td>
            <td class="d-none d-sm-table-cell">
              <TagsSelect
                :modelClass="'attribute'"
                :model="attribute"
                :selectedTags="attribute.tags"
              />
            </td>
            <td class="timestamp-col d-none d-lg-table-cell">
              <Timestamp :timestamp="attribute.timestamp" />
            </td>
            <td class="actions-col text-end">
              <div
                class="d-flex flex-wrap justify-content-end align-items-start gap-1"
              >
                <button
                  type="button"
                  class="btn btn-outline-secondary btn-sm position-relative"
                  :class="{ active: expandedAnalystData.has(attribute.uuid) }"
                  :disabled="loadingAnalystData.has(attribute.uuid)"
                  :title="
                    expandedAnalystData.has(attribute.uuid)
                      ? 'Hide analyst data'
                      : 'Show analyst data'
                  "
                  @click="toggleAnalystData(attribute.uuid)"
                >
                  <!-- the wait shows inside the button, which is a fixed size,
                       so nothing around it moves while the data loads -->
                  <span
                    v-if="loadingAnalystData.has(attribute.uuid)"
                    class="spinner-border spinner-border-sm"
                    role="status"
                    aria-hidden="true"
                  ></span>
                  <FontAwesomeIcon v-else :icon="faCommentDots" />
                  <span
                    v-if="analystDataCount(attribute.uuid) > 0"
                    class="analyst-count badge rounded-pill text-bg-primary"
                  >
                    {{ analystDataCount(attribute.uuid) }}
                    <span class="visually-hidden">analyst data entries</span>
                  </span>
                </button>
                <AttributeActions
                  :attribute="attribute"
                  @attribute-deleted="handleAttributesUpdated"
                  @attribute-enriched="handleAttributesUpdated"
                  @object-created="handleObjectCreated"
                />
              </div>
            </td>
          </tr>
          <tr v-if="expandedAnalystData.has(attribute.uuid)">
            <td colspan="6" class="bg-body-tertiary">
              <AnalystDataIndex
                :object_uuid="attribute.uuid"
                :object_type="'Attribute'"
                @changed="loadAnalystDataCounts"
              />
            </td>
          </tr>
        </template>
      </tbody>
    </table>
    <span v-if="status.loading">
      <FontAwesomeIcon :icon="faSpinner" spin class="ms-2" />
    </span>
    <Paginate
      v-if="page_count > 1"
      :page-count="page_count"
      :click-handler="onPageChange"
    />
    <AddAttributeModal
      id="addAttributeModal"
      @attribute-created="handleAttributesUpdated"
      :modal="addAttributeModal"
      :event_uuid="event_uuid"
    />
    <div class="mt-3">
      <button
        type="button"
        class="w-100 btn btn-outline-primary"
        @click="openAddAttributeModal"
      >
        Add Attribute
      </button>
    </div>
  </div>
</template>
