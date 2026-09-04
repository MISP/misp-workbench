<script setup>
import { ref, computed, onMounted, watch } from "vue";
import { storeToRefs } from "pinia";
import { Modal } from "bootstrap";
import { useAnalystDataStore, useAuthStore } from "@/stores";
import { authHelper } from "@/helpers";
import AnalystDataNode from "@/components/analyst-data/AnalystDataNode.vue";
import CreateOrEditAnalystDataModal from "@/components/analyst-data/CreateOrEditAnalystDataModal.vue";
import DeleteAnalystDataModal from "@/components/analyst-data/DeleteAnalystDataModal.vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import {
  faSpinner,
  faNoteSticky,
  faCommentDots,
  faLink,
} from "@fortawesome/free-solid-svg-icons";

/**
 * Analyst data for one object -- an event, an attribute, an object -- with its
 * threads, and the affordances to add to it.
 *
 * Reads are keyed by object uuid in the store, so several of these can sit on
 * one page (the event plus each of its attributes) without clobbering each
 * other's results.
 */
const props = defineProps({
  object_uuid: { type: String, required: true },
  object_type: { type: String, required: true },
  // when false the list renders without the add buttons, for embedding in a
  // row where space is tight
  show_add: { type: Boolean, default: true },
});

const analystDataStore = useAnalystDataStore();
const { status } = storeToRefs(analystDataStore);
const authStore = useAuthStore();
const { scopes } = storeToRefs(authStore);

const canCreate = computed(() =>
  authHelper.hasScope(scopes.value, "analyst_data:create"),
);

const threads = computed(() => analystDataStore.threadsFor(props.object_uuid));

const nodes = computed(() => [
  ...threads.value.notes,
  ...threads.value.opinions,
  ...threads.value.relationships,
]);

// What the create/edit modal is currently pointed at.
const target = ref({
  object_uuid: props.object_uuid,
  object_type: props.object_type,
  existing: null,
  initial_type: "Note",
});
const nodeToDelete = ref(null);

// Ids are derived from the parent uuid so several of these can coexist on one
// page -- the event card plus one per attribute row -- without colliding.
const createOrEditModalId = computed(
  () => `createOrEditAnalystDataModal_${props.object_uuid}`,
);
const deleteModalId = computed(
  () => `deleteAnalystDataModal_${props.object_uuid}`,
);

let createOrEditModal = null;
let deleteModal = null;

/**
 * `force` refetches even when the store already holds this object's threads.
 * Without it a caller that pre-loaded the data would fetch twice, and the
 * panel would render short, then grow -- which is what made the row jump.
 */
function load(force = false) {
  if (!force && analystDataStore.hasThreadsFor(props.object_uuid)) {
    return Promise.resolve();
  }

  // An event has its own read path: it returns the analyst data attached to
  // the event itself, rather than everything belonging to the event.
  if (props.object_type === "Event") {
    return analystDataStore.getByEventUuid(props.object_uuid);
  }
  return analystDataStore.getByObjectUuid(props.object_uuid, props.object_type);
}

onMounted(() => {
  createOrEditModal = new Modal(
    document.getElementById(createOrEditModalId.value),
  );
  deleteModal = new Modal(document.getElementById(deleteModalId.value));
  load();
});

watch(
  () => props.object_uuid,
  () => load(),
);

function openAdd(initialType) {
  target.value = {
    object_uuid: props.object_uuid,
    object_type: props.object_type,
    existing: null,
    initial_type: initialType,
  };
  createOrEditModal.show();
}

function openReply(node) {
  // A reply hangs off the node, so the node becomes the parent.
  target.value = {
    object_uuid: node.uuid,
    object_type: node.analyst_type,
    existing: null,
    initial_type: "Note",
  };
  createOrEditModal.show();
}

function openEdit(node) {
  target.value = {
    object_uuid: node.object_uuid,
    object_type: node.object_type,
    existing: node,
    initial_type: node.analyst_type,
  };
  createOrEditModal.show();
}

function openDelete(node) {
  nodeToDelete.value = node;
  deleteModal.show();
}

const emit = defineEmits(["changed"]);

function handleChanged() {
  // a write invalidates whatever was cached for this object
  load(true);
  emit("changed");
}
</script>

<template>
  <div>
    <span v-if="status.loading">
      <FontAwesomeIcon :icon="faSpinner" spin />
    </span>

    <div v-if="status.error" class="alert alert-danger" role="alert">
      Error loading analyst data: {{ status.error }}
    </div>

    <div
      v-if="!status.loading && nodes.length === 0"
      class="alert alert-secondary mb-0"
      role="alert"
    >
      No analyst data on this {{ object_type.toLowerCase() }} yet.
    </div>

    <AnalystDataNode
      v-for="node in nodes"
      :key="node.uuid"
      :node="node"
      @reply="openReply"
      @edit="openEdit"
      @delete="openDelete"
    />

    <div v-if="show_add && canCreate" class="mt-3 d-flex gap-2 flex-wrap">
      <button
        type="button"
        class="btn btn-outline-primary btn-sm"
        @click="openAdd('Note')"
      >
        <FontAwesomeIcon :icon="faNoteSticky" class="me-1" /> Add note
      </button>
      <button
        type="button"
        class="btn btn-outline-primary btn-sm"
        @click="openAdd('Opinion')"
      >
        <FontAwesomeIcon :icon="faCommentDots" class="me-1" /> Add opinion
      </button>
      <button
        type="button"
        class="btn btn-outline-primary btn-sm"
        @click="openAdd('Relationship')"
      >
        <FontAwesomeIcon :icon="faLink" class="me-1" /> Add relationship
      </button>
    </div>

    <!-- Not keyed: re-creating these would replace the DOM node the Bootstrap
         Modal instance is bound to, and the next show() would do nothing.
         They reset from their props instead. -->
    <CreateOrEditAnalystDataModal
      :id="createOrEditModalId"
      :modal="createOrEditModal"
      :object_uuid="target.object_uuid"
      :object_type="target.object_type"
      :existing="target.existing"
      :initial_type="target.initial_type"
      @saved="handleChanged"
    />

    <DeleteAnalystDataModal
      :id="deleteModalId"
      :modal="deleteModal"
      :node="nodeToDelete"
      @deleted="handleChanged"
    />
  </div>
</template>
