<script setup>
import { authHelper } from "@/helpers";
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from "vue";
import { Modal } from "bootstrap";
import { storeToRefs } from "pinia";
import {
  useAuthStore,
  useEventsStore,
  useServersStore,
  useToastsStore,
} from "@/stores";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import {
  faTrash,
  faEye,
  faPen,
  faEllipsisVertical,
  faFileArrowUp,
  faSync,
  faStar,
  faUpload,
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

const serversStore = useServersStore();
const toastsStore = useToastsStore();

const pushServers = computed(() => {
  const all = serversStore.servers;
  if (!all || !Array.isArray(all)) return [];
  return all.filter((s) => s.push);
});

const pushing = ref(false);

function pushEventToServer(serverId) {
  pushing.value = true;
  serversStore
    .pushEvent(serverId, props.event_uuid)
    .then((response) => {
      if (response?.status === 200) {
        toastsStore.push(
          response.message || "Event pushed successfully.",
          "success",
        );
      } else {
        toastsStore.push(
          response?.message || "Failed pushing the event.",
          "error",
        );
      }
    })
    .catch((error) => {
      toastsStore.push(
        "Push failed: " +
          (typeof error === "string"
            ? error
            : error?.message || "Unknown error"),
        "error",
      );
    })
    .finally(() => {
      pushing.value = false;
    });
}

function pushEventToAll() {
  pushing.value = true;
  const promises = pushServers.value.map((s) =>
    serversStore.pushEvent(s.id, props.event_uuid),
  );
  Promise.allSettled(promises)
    .then((results) => {
      const failed = results.filter((r) => r.status === "rejected").length;
      if (failed === 0) {
        toastsStore.push(
          `Event pushed to ${results.length} server(s).`,
          "success",
        );
      } else {
        toastsStore.push(
          `Pushed with ${failed} failure(s) out of ${results.length}.`,
          "error",
        );
      }
    })
    .finally(() => {
      pushing.value = false;
    });
}

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

onMounted(() => {
  followed.value = isFollowingEntity("events", props.event_uuid);
  if (
    !serversStore.servers ||
    !Array.isArray(serversStore.servers) ||
    serversStore.servers.length === 0
  ) {
    serversStore.getAll();
  }
});

const deleteModal = ref(null);
const deleteModalRef = ref(null);
const importModal = ref(null);
const importModalRef = ref(null);

function getDeleteModal() {
  if (!deleteModal.value && deleteModalRef.value?.modalEl) {
    deleteModal.value = new Modal(deleteModalRef.value.modalEl);
  }
  return deleteModal.value;
}

function openDeleteEventModal() {
  nextTick(() => {
    getDeleteModal()?.show();
  });
}

function getImportModal() {
  if (!importModal.value && importModalRef.value?.modalEl) {
    importModal.value = new Modal(importModalRef.value.modalEl);
  }
  return importModal.value;
}

function openImportModal() {
  nextTick(() => {
    getImportModal()?.show();
  });
}

onBeforeUnmount(() => {
  deleteModal.value?.dispose();
  importModal.value?.dispose();
});

const emit = defineEmits(["event-updated", "event-deleted"]);

function handleEventDeleted(event) {
  emit("event-deleted", event);
  deleteModal.value?.hide();
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
      <div v-if="pushServers.length" class="btn-group" role="group">
        <button
          type="button"
          class="btn btn-outline-primary btn-sm dropdown-toggle"
          data-bs-toggle="dropdown"
          aria-expanded="false"
          title="Push to server"
          :disabled="pushing"
        >
          <span
            v-if="pushing"
            class="spinner-border spinner-border-sm"
            role="status"
            aria-hidden="true"
          ></span>
          <FontAwesomeIcon v-else :icon="faUpload" fixed-width />
        </button>
        <ul class="dropdown-menu dropdown-menu-end">
          <li>
            <button class="dropdown-item" @click="pushEventToAll">
              Push to all servers
            </button>
          </li>
          <li><hr class="dropdown-divider" /></li>
          <li v-for="server in pushServers" :key="server.id">
            <button class="dropdown-item" @click="pushEventToServer(server.id)">
              {{ server.name }}
            </button>
          </li>
        </ul>
      </div>
      <button
        type="button"
        class="btn btn-outline-primary btn-sm"
        title="Follow Event"
        @click="followEvent"
      >
        <FontAwesomeIcon
          :icon="faStar"
          fixed-width
          :class="followed ? 'text-warning' : 'text-secondary'"
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

      <template v-if="pushServers.length">
        <li><hr class="dropdown-divider" /></li>
        <li>
          <button
            class="dropdown-item"
            :disabled="pushing"
            @click="pushEventToAll"
          >
            <FontAwesomeIcon :icon="faUpload" fixed-width class="me-2" />
            Push to all servers
          </button>
        </li>
        <li v-for="server in pushServers" :key="server.id">
          <button
            class="dropdown-item"
            :disabled="pushing"
            @click="pushEventToServer(server.id)"
          >
            <FontAwesomeIcon :icon="faUpload" fixed-width class="me-2" />
            {{ server.name }}
          </button>
        </li>
      </template>

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
    ref="deleteModalRef"
    :event_uuid="event_uuid"
    @event-deleted="handleEventDeleted"
  />

  <ImportDataEventModal
    ref="importModalRef"
    :event_uuid="event_uuid"
    @event-updated="handleEventUpdated"
  />
</template>
