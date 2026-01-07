<script setup>
import { authHelper } from "@/helpers";
import { ref, onMounted, computed } from "vue";
import { Modal } from "bootstrap";
import { storeToRefs } from "pinia";
import { useModulesStore, useAuthStore } from "@/stores";
import DeleteAttributeModal from "@/components/attributes/DeleteAttributeModal.vue";
import EnrichAttributeModal from "@/components/attributes/EnrichAttributeModal.vue";
import CorrelatedAttributesModal from "@/components/correlations/CorrelatedAttributesModal.vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import {
  faTrash,
  faEye,
  faPen,
  faMagicWandSparkles,
  faSitemap,
  faBookmark,
} from "@fortawesome/free-solid-svg-icons";
import { toggleFollowEntity, isFollowingEntity } from "@/helpers/follow";

const authStore = useAuthStore();
const { scopes } = storeToRefs(authStore);

const followed = ref(false);

const props = defineProps({
  attribute: Object,
  default_actions: {
    type: Object,
    default: () => ({}),
  },
});

const actions = computed(() => ({
  view:
    props.default_actions.view ??
    authHelper.hasScope(scopes.value, "attributes:view"),
  enrich:
    props.default_actions.enrich ??
    authHelper.hasScope(scopes.value, "attributes:enrich"),
  update:
    props.default_actions.update ??
    authHelper.hasScope(scopes.value, "attributes:update"),
  delete:
    props.default_actions.delete ??
    authHelper.hasScope(scopes.value, "attributes:delete"),
  tag:
    props.default_actions.tag ??
    authHelper.hasScope(scopes.value, "attributes:tag"),
}));

const emit = defineEmits([
  "attribute-created",
  "attribute-updated",
  "attribute-deleted",
  "object-created",
  "attribute-enriched",
]);

const deleteAttributeModal = ref(null);
const enrichAttributeModal = ref(null);
const correlatedAttributesModal = ref(null);
const modulesStore = useModulesStore();
const { modulesResponses } = storeToRefs(modulesStore);

onMounted(() => {
  deleteAttributeModal.value = new Modal(
    document.getElementById(`deleteAttributeModal_${props.attribute.id}`),
  );
  enrichAttributeModal.value = new Modal(
    document.getElementById(`enrichAttributeModal_${props.attribute.id}`),
  );
  correlatedAttributesModal.value = new Modal(
    document.getElementById(`correlatedAttributesModal${props.attribute.id}`),
  );
  followed.value = isFollowingEntity("attributes", props.attribute.uuid);
});

function openDeleteAttributeModal() {
  deleteAttributeModal.value.show();
}

function openEnrichAttributeModal() {
  modulesResponses.value = [];
  enrichAttributeModal.value.show();
}

function openCorrelationsModal() {
  correlatedAttributesModal.value.show();
}

function handleAttributeDeleted() {
  emit("attribute-deleted", props.attribute.id);
}

function handleAttributeEnriched() {
  emit("attribute-enriched", props.attribute.id);
}

function followAttribute() {
  followed.value = !followed.value;
  toggleFollowEntity("attributes", props.attribute.uuid, followed.value);
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
    <div
      v-if="Object(attribute.correlations).length > 0"
      class="btn-group me-2"
      role="group"
    >
      <button
        type="button"
        class="btn btn-sm"
        @click="openCorrelationsModal"
        title="View Correlations"
      >
        <FontAwesomeIcon :icon="faSitemap" class="text-warning" />
      </button>
    </div>

    <div class="btn-group me-2" role="group">
      <button
        v-if="actions.enrich"
        type="button"
        class="btn btn-outline-primary btn-sm"
        title="Enrich Attribute"
        @click="openEnrichAttributeModal"
      >
        <FontAwesomeIcon fixed-width :icon="faMagicWandSparkles" />
      </button>

      <button
        type="button"
        class="btn btn-outline-primary btn-sm"
        title="Follow Attribute"
        @click="followAttribute"
      >
        <FontAwesomeIcon
          fixed-width
          :icon="faBookmark"
          :class="followed ? 'text-success' : 'text-primary'"
        />
      </button>
    </div>

    <div class="btn-group me-2" role="group">
      <RouterLink
        v-if="actions.view"
        :to="`/attributes/${attribute.id}`"
        class="btn btn-outline-primary btn-sm"
        title="View Attribute"
      >
        <FontAwesomeIcon fixed-width :icon="faEye" />
      </RouterLink>

      <RouterLink
        v-if="actions.update"
        :to="`/attributes/update/${attribute.id}`"
        class="btn btn-outline-primary btn-sm"
        title="Update Attribute"
      >
        <FontAwesomeIcon fixed-width :icon="faPen" />
      </RouterLink>

      <button
        v-if="actions.delete"
        type="button"
        class="btn btn-danger btn-sm"
        title="Delete Attribute"
        @click="openDeleteAttributeModal"
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
      <li v-if="Object(attribute.correlations).length > 0">
        <button class="dropdown-item" @click="openCorrelationsModal">
          <FontAwesomeIcon :icon="faSitemap" class="me-2 text-warning" />
          Correlations
        </button>
      </li>

      <li v-if="actions.view">
        <RouterLink class="dropdown-item" :to="`/attributes/${attribute.id}`">
          <FontAwesomeIcon :icon="faEye" class="me-2" />
          View
        </RouterLink>
      </li>

      <li v-if="actions.update">
        <RouterLink
          class="dropdown-item"
          :to="`/attributes/update/${attribute.id}`"
        >
          <FontAwesomeIcon :icon="faPen" class="me-2" />
          Update
        </RouterLink>
      </li>

      <li v-if="actions.enrich">
        <button class="dropdown-item" @click="openEnrichAttributeModal">
          <FontAwesomeIcon :icon="faMagicWandSparkles" class="me-2" />
          Enrich
        </button>
      </li>

      <li>
        <button class="dropdown-item" @click="followAttribute">
          <FontAwesomeIcon
            :icon="faBookmark"
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
          @click="openDeleteAttributeModal"
        >
          <FontAwesomeIcon :icon="faTrash" class="me-2" />
          Delete
        </button>
      </li>
    </ul>
  </div>

  <DeleteAttributeModal
    :key="attribute.id"
    :id="`deleteAttributeModal_${attribute.id}`"
    @attribute-deleted="handleAttributeDeleted"
    :modal="deleteAttributeModal"
    :attribute_id="attribute.id"
  />

  <EnrichAttributeModal
    :key="attribute.id"
    :id="`enrichAttributeModal_${attribute.id}`"
    @attribute-enriched="handleAttributeEnriched"
    :modal="enrichAttributeModal"
    :attribute="attribute"
  />

  <CorrelatedAttributesModal
    :key="attribute.id"
    :id="`correlatedAttributesModal${attribute.id}`"
    :modal="correlatedAttributesModal"
    :attribute="attribute"
  />
</template>
