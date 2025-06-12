<script setup>
import { authHelper } from "@/helpers";
import { ref, onMounted, computed } from "vue";
import { Modal } from "bootstrap";
import { storeToRefs } from "pinia";
import { useModulesStore, useAuthStore } from "@/stores";
import DeleteAttributeModal from "@/components/attributes/DeleteAttributeModal.vue";
import EnrichAttributeModal from "@/components/attributes/EnrichAttributeModal.vue";
import AttributeCorrelationsModal from "@/components/attributes/AttributeCorrelationsModal.vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import {
  faTrash,
  faEye,
  faPen,
  faMagicWandSparkles,
  faSitemap,
} from "@fortawesome/free-solid-svg-icons";

const authStore = useAuthStore();
const { scopes } = storeToRefs(authStore);

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
const atributeCorrelationsModal = ref(null);
const modulesStore = useModulesStore();
const { modulesResponses } = storeToRefs(modulesStore);

onMounted(() => {
  deleteAttributeModal.value = new Modal(
    document.getElementById(`deleteAttributeModal_${props.attribute.id}`),
  );
  enrichAttributeModal.value = new Modal(
    document.getElementById(`enrichAttributeModal_${props.attribute.id}`),
  );
  atributeCorrelationsModal.value = new Modal(
    document.getElementById(`attributeCorrelationsModal_${props.attribute.id}`),
  );
});

function openDeleteAttributeModal() {
  deleteAttributeModal.value.show();
}

function openEnrichAttributeModal() {
  modulesResponses.value = [];
  enrichAttributeModal.value.show();
}

function openCorrelationsModal() {
  atributeCorrelationsModal.value.show();
}

function handleAttributeDeleted() {
  emit("attribute-deleted", props.attribute.id);
}

function handleAttributeEnriched() {
  emit("attribute-enriched", props.attribute.id);
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
        class="btn btn-outline-primary"
        @click="openCorrelationsModal"
        data-placement="top"
        data-toggle="tooltip"
        title="View Correlations"
      >
        <FontAwesomeIcon :icon="faSitemap" />
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
        class="btn btn-outline-primary"
        data-placement="top"
        data-toggle="tooltip"
        title="View Attribute"
      >
        <FontAwesomeIcon :icon="faEye" />
      </RouterLink>
      <button
        v-if="actions.enrich"
        type="button"
        class="btn btn-outline-primary"
        @click="openEnrichAttributeModal"
        data-placement="top"
        data-toggle="tooltip"
        title="Enrich Attribute"
      >
        <FontAwesomeIcon :icon="faMagicWandSparkles" />
      </button>
      <RouterLink
        v-if="actions.update"
        :to="`/attributes/update/${attribute.id}`"
        class="btn btn-outline-primary"
        data-placement="top"
        data-toggle="tooltip"
        title="Update Attribute"
      >
        <FontAwesomeIcon :icon="faPen" />
      </RouterLink>
    </div>
    <div class="btn-group me-2" role="group">
      <button
        v-if="actions.delete"
        type="button"
        class="btn btn-danger"
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
  <AttributeCorrelationsModal
    :key="attribute.id"
    :id="`attributeCorrelationsModal_${attribute.id}`"
    :modal="AttributeCorrelationsModal"
    :attribute="attribute"
  />
</template>
