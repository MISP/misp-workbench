<script setup>
import { ref, onMounted, computed } from "vue";
import { storeToRefs } from "pinia";
import { Modal } from "bootstrap";
import DeleteObjectModal from "@/components/objects/DeleteObjectModal.vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import {
  faTrash,
  faEye,
  faPen,
  faMagicWandSparkles,
  faStar,
} from "@fortawesome/free-solid-svg-icons";
import { authHelper } from "@/helpers";
import { useAuthStore } from "@/stores";
import { toggleFollowEntity, isFollowingEntity } from "@/helpers/follow";

const authStore = useAuthStore();
const { scopes } = storeToRefs(authStore);

const props = defineProps({
  object: Object,
  default_actions: {
    type: Object,
    default: () => ({}),
  },
});

const emit = defineEmits([
  "object-created",
  "object-updated",
  "object-deleted",
  "object-created",
  //   "object-enriched",
]);

const actions = computed(() => ({
  view:
    props.default_actions.view ??
    authHelper.hasScope(scopes.value, "objects:view"),
  enrich:
    props.default_actions.enrich ??
    authHelper.hasScope(scopes.value, "objects:enrich"),
  update:
    props.default_actions.update ??
    authHelper.hasScope(scopes.value, "objects:update"),
  delete:
    props.default_actions.delete ??
    authHelper.hasScope(scopes.value, "objects:delete"),
  tag:
    props.default_actions.tag ??
    authHelper.hasScope(scopes.value, "objects:tag"),
}));

const followed = ref(false);

const deleteObjectModal = ref(null);
onMounted(() => {
  deleteObjectModal.value = new Modal(
    document.getElementById(`deleteObjectModal_${props.object.id}`),
  );
  followed.value = isFollowingEntity("objects", props.object.uuid);
});

function openDeleteObjectModal() {
  deleteObjectModal.value.show();
}

function handleObjectDeleted() {
  emit("object-deleted", props.object.id);
}

function followObject() {
  followed.value = !followed.value;
  toggleFollowEntity("objects", props.object.uuid, followed.value);
}

// function handleObjectEnriched() {
//   emit("object-enriched", props.object.id);
// }
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
}
</style>

<template>
  <!-- DESKTOP ACTIONS -->
  <div
    v-if="!$isMobile"
    class="btn-toolbar d-flex align-items-center flex-nowrap float-end"
    role="toolbar"
  >
    <div class="btn-group me-2" role="group">
      <RouterLink
        v-if="actions.view"
        :to="`/objects/${object.id}`"
        class="btn btn-outline-primary btn-sm"
        title="View Object"
      >
        <FontAwesomeIcon fixed-width :icon="faEye" />
      </RouterLink>

      <RouterLink
        v-if="actions.update"
        :to="`/objects/update/${object.id}`"
        class="btn btn-outline-primary btn-sm"
        title="Update Object"
      >
        <FontAwesomeIcon fixed-width :icon="faPen" />
      </RouterLink>
    </div>

    <div class="btn-group me-2" role="group">
      <button
        v-if="actions.enrich"
        type="button"
        class="btn btn-outline-primary btn-sm disabled"
        title="Enrich Object"
      >
        <FontAwesomeIcon fixed-width :icon="faMagicWandSparkles" />
      </button>

      <button
        type="button"
        class="btn btn-outline-primary btn-sm"
        title="Follow Object"
        @click="followObject"
      >
        <FontAwesomeIcon
          fixed-width
          :icon="faStar"
          :class="followed ? 'text-success' : 'text-primary'"
        />
      </button>
    </div>

    <div class="btn-group" role="group">
      <button
        v-if="actions.delete"
        type="button"
        class="btn btn-danger btn-sm"
        title="Delete Object"
        @click="openDeleteObjectModal"
      >
        <FontAwesomeIcon fixed-width :icon="faTrash" />
      </button>
    </div>
  </div>

  <div v-else class="dropdown float-end">
    <button
      class="btn btn-outline-secondary btn-sm"
      type="button"
      data-bs-toggle="dropdown"
      aria-expanded="false"
    >
      &#8230;
    </button>

    <ul class="dropdown-menu dropdown-menu-end">
      <li v-if="actions.view">
        <RouterLink class="dropdown-item" :to="`/objects/${object.id}`">
          <FontAwesomeIcon :icon="faEye" class="me-2" />
          View
        </RouterLink>
      </li>

      <li v-if="actions.update">
        <RouterLink class="dropdown-item" :to="`/objects/update/${object.id}`">
          <FontAwesomeIcon :icon="faPen" class="me-2" />
          Update
        </RouterLink>
      </li>

      <li v-if="actions.enrich">
        <button class="dropdown-item disabled">
          <FontAwesomeIcon :icon="faMagicWandSparkles" class="me-2" />
          Enrich
        </button>
      </li>

      <li>
        <button class="dropdown-item" @click="followObject">
          <FontAwesomeIcon
            :icon="faStar"
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
        <button
          class="dropdown-item text-danger"
          @click="openDeleteObjectModal"
        >
          <FontAwesomeIcon :icon="faTrash" class="me-2" />
          Delete
        </button>
      </li>
    </ul>
  </div>

  <!-- MODALS -->
  <DeleteObjectModal
    :key="object.id"
    :id="`deleteObjectModal_${object.id}`"
    @object-deleted="handleObjectDeleted"
    :modal="deleteObjectModal"
    :object_id="object.id"
  />
</template>
