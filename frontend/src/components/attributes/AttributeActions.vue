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
  faStar,
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
    document.getElementById(`deleteAttributeModal_${props.attribute.uuid}`),
  );
  enrichAttributeModal.value = new Modal(
    document.getElementById(`enrichAttributeModal_${props.attribute.uuid}`),
  );
  correlatedAttributesModal.value = new Modal(
    document.getElementById(`correlatedAttributesModal${props.attribute.uuid}`),
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
  emit("attribute-deleted", props.attribute.uuid);
}

function handleAttributeEnriched() {
  emit("attribute-enriched", props.attribute.uuid);
}

function handleObjectCreated(object) {
  emit("object-created", object);
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
          :icon="faStar"
          :class="followed ? 'text-warning' : 'text-secondary'"
        />
      </button>
    </div>

    <div class="btn-group me-2" role="group">
      <RouterLink
        v-if="actions.view"
        :to="`/attributes/${attribute.uuid}`"
        class="btn btn-outline-primary btn-sm"
        title="View Attribute"
      >
        <FontAwesomeIcon fixed-width :icon="faEye" />
      </RouterLink>

      <RouterLink
        v-if="actions.update"
        :to="`/attributes/update/${attribute.uuid}`"
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
        <RouterLink class="dropdown-item" :to="`/attributes/${attribute.uuid}`">
          <FontAwesomeIcon :icon="faEye" class="me-2" />
          View
        </RouterLink>
      </li>

      <li v-if="actions.update">
        <RouterLink
          class="dropdown-item"
          :to="`/attributes/update/${attribute.uuid}`"
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
          @click="openDeleteAttributeModal"
        >
          <FontAwesomeIcon :icon="faTrash" class="me-2" />
          Delete
        </button>
      </li>
    </ul>
  </div>

  <DeleteAttributeModal
    :key="attribute.uuid"
    :id="`deleteAttributeModal_${attribute.uuid}`"
    @attribute-deleted="handleAttributeDeleted"
    :modal="deleteAttributeModal"
    :attribute_uuid="attribute.uuid"
  />

  <EnrichAttributeModal
    :key="attribute.uuid"
    :id="`enrichAttributeModal_${attribute.uuid}`"
    @attribute-enriched="handleAttributeEnriched"
    @object-created="handleObjectCreated"
    :modal="enrichAttributeModal"
    :attribute="attribute"
  />

  <CorrelatedAttributesModal
    :key="attribute.uuid"
    :id="`correlatedAttributesModal${attribute.uuid}`"
    :modal="correlatedAttributesModal"
    :attribute="attribute"
  />
</template>
