<script setup>
import { authHelper } from "@/helpers";
import { ref, computed, onMounted } from "vue";
import { Modal } from "bootstrap";
import { storeToRefs } from "pinia";
import { useAuthStore } from "@/stores";
import DeleteEventModal from "@/components/events/DeleteEventModal.vue";

const authStore = useAuthStore();
const { scopes } = storeToRefs(authStore);

const props = defineProps({
  event_id: Number,
  default_actions: {
    type: Object,
    default: () => ({}),
  },
});

const actions = computed(() => ({
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
      >
        <font-awesome-icon icon="fa-solid fa-eye" />
      </RouterLink>
      <RouterLink
        v-if="actions.update"
        :to="`/events/update/${event_id}`"
        class="btn btn-outline-primary"
      >
        <font-awesome-icon icon="fa-solid fa-pen" />
      </RouterLink>
    </div>
    <div class="btn-group me-2" role="group">
      <button
        v-if="actions.delete"
        type="button"
        class="btn btn-danger"
        data-placement="top"
        title="Delete Event"
        @click="openDeleteEventModal"
      >
        <font-awesome-icon icon="fa-solid fa-trash" />
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
