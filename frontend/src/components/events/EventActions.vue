<script setup>
import { authHelper } from "@/helpers";
import { ref, computed, onMounted } from "vue";
import { Modal } from "bootstrap";
import { storeToRefs } from "pinia";
import { useAuthStore, useEventsStore } from "@/stores";
import DeleteEventModal from "@/components/events/DeleteEventModal.vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import {
  faTrash,
  faEye,
  faPen,
  faFileArrowUp,
  faSync,
} from "@fortawesome/free-solid-svg-icons";

const authStore = useAuthStore();
const { scopes } = storeToRefs(authStore);

const eventsStore = useEventsStore();
const { status } = storeToRefs(eventsStore);

const props = defineProps({
  event_id: Number,
  default_actions: {
    type: Object,
    default: () => ({}),
  },
});

const actions = computed(() => ({
  index:
    props.default_actions.index ??
    authHelper.hasScope(scopes.value, "events:index"),
  view:
    props.default_actions.view ??
    authHelper.hasScope(scopes.value, "events:view"),
  update:
    props.default_actions.update ??
    authHelper.hasScope(scopes.value, "events:update"),
  delete:
    props.default_actions.delete ??
    authHelper.hasScope(scopes.value, "events:delete"),
  tag:
    props.default_actions.tag ??
    authHelper.hasScope(scopes.value, "events:tag"),
}));

const deleteEventModal = ref(null);

onMounted(() => {
  deleteEventModal.value = new Modal(
    document.getElementById(`deleteEventModal_${props.event_id}`),
  );
});

function openDeleteEventModal() {
  deleteEventModal.value.show();
}

const emit = defineEmits(["event-updated", "event-deleted"]);

function handleEventDeleted(event) {
  emit("event-deleted", event);
}

function indexEventDocument() {
  eventsStore.forceIndex(props.event_id);
}
</script>

<style scoped>
.btn-toolbar {
  flex-wrap: nowrap !important;
}
</style>

<template>
  <div class="btn-toolbar float-end" role="toolbar">
    <div
      :class="{ 'btn-group-vertical': $isMobile, 'btn-group me-2': !$isMobile }"
      role="group"
      aria-label="Event Actions"
    >
      <RouterLink
        v-if="actions.view"
        :to="`/events/${event_id}`"
        class="btn btn-outline-primary"
        data-placement="top"
        data-toggle="tooltip"
        title="View Event"
      >
        <FontAwesomeIcon :icon="faEye" />
      </RouterLink>
      <RouterLink
        v-if="actions.update"
        :to="`/events/update/${event_id}`"
        class="btn btn-outline-primary"
        data-placement="top"
        data-toggle="tooltip"
        title="Update Event"
      >
        <FontAwesomeIcon :icon="faPen" />
      </RouterLink>
    </div>
    <div class="btn-group me-2" role="group">
      <button
        v-if="actions.index"
        :disabled="status.indexing"
        type="button"
        class="btn btn-outline-primary"
        data-placement="top"
        data-toggle="tooltip"
        title="Index Event"
        @click="indexEventDocument"
      >
        <FontAwesomeIcon v-if="!status.indexing" :icon="faFileArrowUp" />
        <FontAwesomeIcon v-if="status.indexing" :icon="faSync" spin />
      </button>
    </div>
    <div class="btn-group me-2" role="group">
      <button
        v-if="actions.delete"
        type="button"
        class="btn btn-danger"
        data-placement="top"
        data-toggle="tooltip"
        title="Delete Event"
        @click="openDeleteEventModal"
      >
        <FontAwesomeIcon :icon="faTrash" />
      </button>
    </div>
  </div>
  <DeleteEventModal
    :key="event_id"
    :id="`deleteEventModal_${event_id}`"
    @event-deleted="handleEventDeleted"
    :modal="deleteEventModal"
    :event_id="event_id"
  />
</template>
