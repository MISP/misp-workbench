<script setup>
import { authHelper } from "@/helpers";
import { ref, computed, onMounted, onBeforeUnmount } from "vue";
import { Modal } from "bootstrap";
import { storeToRefs } from "pinia";
import { useAuthStore } from "@/stores";
import DeleteTaxonomyModal from "@/components/taxonomies/DeleteTaxonomyModal.vue";

const authStore = useAuthStore();
const { scopes } = storeToRefs(authStore);

const props = defineProps(["taxonomy"]);
const emit = defineEmits(["taxonomy-deleted"]);

const actions = computed(() => ({
  view: authHelper.hasScope(scopes.value, "taxonomies:read"),
  delete: authHelper.hasScope(scopes.value, "taxonomies:delete"),
}));

const deleteTaxonomyModal = ref(null);

onMounted(() => {
  deleteTaxonomyModal.value = new Modal(
    document.getElementById(`deleteTaxonomyModal_${props.taxonomy.id}`),
  );
});

onBeforeUnmount(() => {
  deleteTaxonomyModal.value?.dispose();
});

function openDeleteTaxonomyModal() {
  deleteTaxonomyModal.value?.show();
}

function handleTaxonomyDeleted() {
  emit("taxonomy-deleted", props.taxonomy.id);
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
      aria-label="Taxonomy Actions"
    >
      <RouterLink
        v-if="actions.view"
        :to="`/taxonomies/${taxonomy.id}`"
        class="btn btn-outline-primary btn-sm"
      >
        <font-awesome-icon icon="fa-solid fa-eye" />
      </RouterLink>
    </div>
    <div v-if="actions.delete" class="btn-group me-2" role="group">
      <button
        type="button"
        class="btn btn-danger btn-sm"
        @click="openDeleteTaxonomyModal"
      >
        <font-awesome-icon icon="fa-solid fa-trash" />
      </button>
    </div>
  </div>
  <DeleteTaxonomyModal
    :key="taxonomy.id"
    :id="`deleteTaxonomyModal_${taxonomy.id}`"
    @taxonomy-deleted="handleTaxonomyDeleted"
    :modal="deleteTaxonomyModal"
    :taxonomy_id="taxonomy.id"
  />
</template>
