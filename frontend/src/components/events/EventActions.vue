<script setup>
import { authHelper } from "@/helpers";
import { ref, computed, onMounted } from "vue";
import { Modal } from "bootstrap";
import { storeToRefs } from "pinia";
import { useAuthStore, useEventsStore } from "@/stores";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import {
  faTrash,
  faEye,
  faPen,
  faEllipsisVertical,
  faFileArrowUp,
  faSync,
  faStar,
  // faArrowsRotate,
  faFileImport,
} from "@fortawesome/free-solid-svg-icons";
import { toggleFollowEntity, isFollowingEntity } from "@/helpers/follow";
import DeleteEventModal from "@/components/events/DeleteEventModal.vue";
import ImportDataEventModal from "@/components/events/ImportDataEventModal.vue";

const authStore = useAuthStore();
const { scopes } = storeToRefs(authStore);

const eventsStore = useEventsStore();
const { status } = storeToRefs(eventsStore);

const followed = ref(false);

const props = defineProps({
  event_uuid: String,
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
const importDataEventModal = ref(null);

onMounted(() => {
  deleteEventModal.value = new Modal(
    document.getElementById(`deleteEventModal_${props.event_uuid}`),
  );
  importDataEventModal.value = new Modal(
    document.getElementById(`importDataEventModal_${props.event_uuid}`),
  );
  followed.value = isFollowingEntity("events", props.event_uuid);
});

function openDeleteEventModal() {
  deleteEventModal.value.show();
}

function openImportModal() {
  importDataEventModal.value.show();
}

const emit = defineEmits(["event-updated", "event-deleted"]);

function handleEventDeleted(event) {
  emit("event-deleted", event);
}

function handleEventUpdated(event) {
  emit("event-updated", event);
}

function indexEventDocument() {
  eventsStore.forceIndex(props.event_uuid);
}

function followEvent() {
  followed.value = !followed.value;
  toggleFollowEntity("events", props.event_uuid, followed.value);
}
</script>

<style scoped>
.btn-toolbar {
  display: flex;
  gap: 0.25rem;
}

@media (max-width: 576px) {
  .btn-toolbar {
    flex-wrap: wrap !important;
    width: 100%;
  }

  .btn-group,
  .btn-group-vertical {
    width: 100%;
  }

  .btn-group .btn,
  .btn-group-vertical .btn {
    width: 100%;
    justify-content: center;
  }
}
</style>

<template>
  <div
    v-if="!$isMobile"
    class="btn-toolbar d-flex align-items-center flex-nowrap float-end"
    role="toolbar"
  >
    <div class="btn-group me-2" role="group">
      <button
        v-if="actions.index"
        type="button"
        class="btn btn-outline-primary btn-sm"
        :disabled="status.indexing"
        title="Import"
        @click="openImportModal"
      >
        <FontAwesomeIcon :icon="faFileImport" fixed-width />
      </button>
      <!-- <button
        v-if="actions.index"
        type="button"
        class="btn btn-outline-primary btn-sm"
        :disabled="status.indexing"
        title="Re-Index Event"
        @click="indexEventDocument"
      >
        <FontAwesomeIcon
          v-if="!status.indexing"
          :icon="faArrowsRotate"
          fixed-width
        />
        <FontAwesomeIcon v-else :icon="faSync" fixed-width spin />
      </button> -->
      <button
        type="button"
        class="btn btn-outline-primary btn-sm"
        title="Follow Event"
        @click="followEvent"
      >
        <FontAwesomeIcon
          :icon="faStar"
          fixed-width
          :class="followed ? 'text-success' : 'text-primary'"
        />
      </button>
    </div>
    <div class="btn-group me-2" role="group" aria-label="Event Actions">
      <RouterLink
        v-if="actions.view"
        :to="`/events/${event_uuid}`"
        class="btn btn-outline-primary btn-sm"
        title="View Event"
      >
        <FontAwesomeIcon :icon="faEye" fixed-width />
      </RouterLink>

      <RouterLink
        v-if="actions.update"
        :to="`/events/update/${event_uuid}`"
        class="btn btn-outline-primary btn-sm"
        title="Update Event"
      >
        <FontAwesomeIcon :icon="faPen" fixed-width />
      </RouterLink>

      <button
        v-if="actions.delete"
        type="button"
        class="btn btn-danger btn-sm"
        title="Delete Event"
        @click="openDeleteEventModal"
      >
        <FontAwesomeIcon :icon="faTrash" fixed-width />
      </button>
    </div>
  </div>

  <div v-else class="dropdown text-end">
    <button
      class="btn btn-outline-secondary btn-sm"
      type="button"
      data-bs-toggle="dropdown"
      aria-expanded="false"
      aria-label="Event actions"
    >
      <FontAwesomeIcon :icon="faEllipsisVertical" fixed-width />
    </button>

    <ul class="dropdown-menu dropdown-menu-end">
      <li v-if="actions.view">
        <RouterLink :to="`/events/${event_uuid}`" class="dropdown-item">
          <FontAwesomeIcon :icon="faEye" fixed-width class="me-2" />
          View
        </RouterLink>
      </li>

      <li v-if="actions.update">
        <RouterLink :to="`/events/update/${event_uuid}`" class="dropdown-item">
          <FontAwesomeIcon :icon="faPen" fixed-width class="me-2" />
          Edit
        </RouterLink>
      </li>

      <li v-if="actions.index">
        <button
          class="dropdown-item"
          :disabled="status.indexing"
          @click="indexEventDocument"
        >
          <FontAwesomeIcon
            :icon="status.indexing ? faSync : faFileArrowUp"
            fixed-width
            class="me-2"
            :spin="status.indexing"
          />
          Index
        </button>
      </li>

      <li>
        <button class="dropdown-item" @click="followEvent">
          <FontAwesomeIcon
            :icon="faStar"
            fixed-width
            class="me-2"
            :class="followed ? 'text-success' : 'text-primary'"
          />
          {{ followed ? "Unfollow" : "Follow" }}
        </button>
      </li>

      <li>
        <hr class="dropdown-divider" />
      </li>

      <li v-if="actions.delete">
        <button class="dropdown-item text-danger" @click="openDeleteEventModal">
          <FontAwesomeIcon :icon="faTrash" fixed-width class="me-2" />
          Delete
        </button>
      </li>
    </ul>
  </div>

  <DeleteEventModal
    :key="event_uuid"
    :id="`deleteEventModal_${event_uuid}`"
    @event-deleted="handleEventDeleted"
    :modal="deleteEventModal"
    :event_uuid="event_uuid"
  />

  <ImportDataEventModal
    :key="event_uuid"
    :id="`importDataEventModal_${event_uuid}`"
    @event-updated="handleEventUpdated"
    :modal="importDataEventModal"
    :event_uuid="event_uuid"
  />
</template>
