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
  flex-wrap: nowrap !important;
}
</style>

<template>
  <div class="btn-toolbar float-end" role="toolbar">
    <div
      v-if="Object(attribute.correlations).length > 0"
      class="btn-group me-2"
      role="group"
    >
      <button
        type="button"
        class="btn"
        @click="openCorrelationsModal"
        data-placement="top"
        data-toggle="tooltip"
        title="View Correlations"
      >
        <FontAwesomeIcon :icon="faSitemap" class="text-warning" />
      </button>
    </div>
    <div
      :class="{ 'btn-group-vertical': $isMobile, 'btn-group me-2': !$isMobile }"
      role="group"
      aria-label="Attribute Actions"
    >
      <RouterLink
        v-if="actions.view"
        :to="`/attributes/${attribute.id}`"
        class="btn btn-outline-primary btn-sm"
        data-placement="top"
        data-toggle="tooltip"
        title="View Attribute"
      >
        <FontAwesomeIcon :icon="faEye" />
      </RouterLink>
      <RouterLink
        v-if="actions.update"
        :to="`/attributes/update/${attribute.id}`"
        class="btn btn-outline-primary btn-sm"
        data-placement="top"
        data-toggle="tooltip"
        title="Update Attribute"
      >
        <FontAwesomeIcon :icon="faPen" />
      </RouterLink>
    </div>
    <div class="btn-group me-2" role="group">
      <button
        v-if="actions.enrich"
        type="button"
        class="btn btn-outline-primary btn-sm"
        @click="openEnrichAttributeModal"
        data-placement="top"
        data-toggle="tooltip"
        title="Enrich Attribute"
      >
        <FontAwesomeIcon :icon="faMagicWandSparkles" />
      </button>
      <button
        type="button"
        class="btn btn-outline-primary btn-sm"
        data-placement="top"
        data-toggle="tooltip"
        title="Follow Attribute"
        @click="followAttribute"
      >
        <FontAwesomeIcon
          v-if="!followed"
          :icon="faBookmark"
          :inverse="true"
          class="text-light"
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
        @click="openDeleteAttributeModal"
        data-placement="top"
        data-toggle="tooltip"
        title="Delete Attribute"
      >
        <FontAwesomeIcon :icon="faTrash" />
      </button>
    </div>
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
