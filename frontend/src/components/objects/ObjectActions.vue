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
  faBookmark,
} from "@fortawesome/free-solid-svg-icons";
import { authHelper } from "@/helpers";
import { useAuthStore } from "@/stores";
import { toggleFollowEntity, isFollowingEntity } from "@/helpers/follow";
// import { useModulesStore } from "@/stores";
// import EnrichObjectModal from "@/components/objects/EnrichObjectModal.vue";

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
// const enrichObjectModal = ref(null);
// const modulesStore = useModulesStore();
// const { modulesResponses } = storeToRefs(modulesStore);

onMounted(() => {
  deleteObjectModal.value = new Modal(
    document.getElementById(`deleteObjectModal_${props.object.id}`),
  );
  followed.value = isFollowingEntity("objects", props.object.uuid);
  //   enrichObjectModal.value = new Modal(
  //     document.getElementById(`enrichObjectModal_${props.object.id}`),
  //   );
});

function openDeleteObjectModal() {
  deleteObjectModal.value.show();
}

function openEnrichObjectModal() {
  //   modulesResponses.value = [];
  //   enrichObjectModal.value.show();
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
  flex-wrap: nowrap !important;
}
</style>

<template>
  <div class="btn-toolbar float-end" role="toolbar">
    <div
      :class="{ 'btn-group-vertical': $isMobile, 'btn-group me-2': !$isMobile }"
      role="group"
      aria-label="Object Actions"
    >
      <RouterLink
        v-if="actions.view"
        :to="`/objects/${object.id}`"
        class="btn btn-outline-primary btn-sm"
      >
        <FontAwesomeIcon :icon="faEye" />
      </RouterLink>
      <!-- <button
        type="button"
        class="btn btn-outline-primary btn-sm"
        @click="openEnrichObjectModal"
      >
        <font-awesome-icon icon="fa-solid fa-magic-wand-sparkles" />
      </button> -->
      <RouterLink
        v-if="actions.update"
        :to="`/objects/update/${object.id}`"
        class="btn btn-outline-primary btn-sm"
      >
        <FontAwesomeIcon :icon="faPen" />
      </RouterLink>
    </div>
    <div class="btn-group me-2" role="group">
      <button
        v-if="actions.enrich"
        type="button"
        class="btn btn-outline-primary btn-sm disabled"
        @click="openEnrichObjectModal"
        data-placement="top"
        data-toggle="tooltip"
        title="Enrich Object"
      >
        <FontAwesomeIcon :icon="faMagicWandSparkles" />
      </button>
      <button
        type="button"
        class="btn btn-outline-primary btn-sm"
        data-placement="top"
        data-toggle="tooltip"
        title="Follow Object"
        @click="followObject"
      >
        <FontAwesomeIcon
          v-if="!followed"
          :icon="faBookmark"
          :inverse="true"
          class="text-primary"
        />
        <FontAwesomeIcon
          v-if="followed"
          :icon="faBookmark"
          class="text-success"
        />
      </button>
    </div>
    <div class="btn-group me-2" role="group">
      <button
        v-if="actions.delete"
        type="button"
        class="btn btn-danger btn-sm"
        @click="openDeleteObjectModal"
      >
        <FontAwesomeIcon :icon="faTrash" />
      </button>
    </div>
  </div>
  <DeleteObjectModal
    :key="object.id"
    :id="`deleteObjectModal_${object.id}`"
    @object-deleted="handleObjectDeleted"
    :modal="deleteObjectModal"
    :object_id="object.id"
  />
  <!-- <EnrichObjectModal
    :key="object.id"
    :id="`enrichObjectModal_${object.id}`"
    @object-enriched="handleObjectEnriched"
    :modal="enrichObjectModal"
    :object="object"
  /> -->
</template>
