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
import { faSpinner, faCommentDots } from "@fortawesome/free-solid-svg-icons";

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
    <table class="table table-striped">
      <thead>
        <tr>
          <th scope="col">value</th>
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
          <tr>
            <td class="value">
              <CopyToClipboard :value="attribute.value" />
              {{ attribute.value }}
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
            <td colspan="5" class="bg-body-tertiary">
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
