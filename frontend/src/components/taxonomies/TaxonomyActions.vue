<script setup>
import { ref, onMounted } from 'vue';
import { Modal } from 'bootstrap';
import DeleteTaxonomyModal from "@/components/taxonomies/DeleteTaxonomyModal.vue";

const props = defineProps(['taxonomy']);
const emit = defineEmits(['taxonomy-deleted']);

const deleteTaxonomyModal = ref(null);

onMounted(() => {
    deleteTaxonomyModal.value = new Modal(document.getElementById(`deleteTaxonomyModal_${props.taxonomy.id}`));
});

function openDeleteTaxonomyModal() {
    deleteTaxonomyModal.value.show();
}

function handleTaxonomyDeleted() {
    emit('taxonomy-deleted', props.taxonomy.id);
}
</script>

<style scoped>
.btn-toolbar {
    flex-wrap: nowrap !important;
}
</style>

<template>
    <div class="btn-toolbar float-end" role="toolbar">
        <div :class="{ 'btn-group-vertical': $isMobile, 'btn-group me-2': !$isMobile }" role="group"
            aria-label="Taxonomy Actions">
            <RouterLink :to="`/taxonomies/${taxonomy.id}`" tag="button" class="btn btn-outline-primary">
                <font-awesome-icon icon="fa-solid fa-eye" />
            </RouterLink>
        </div>
        <div class="btn-group me-2" role="group">
            <button type="button" class="btn btn-danger" @click="openDeleteTaxonomyModal">
                <font-awesome-icon icon="fa-solid fa-trash" />
            </button>
        </div>
    </div>
    <DeleteTaxonomyModal :key="taxonomy.id" :id="`deleteTaxonomyModal_${taxonomy.id}`"
        @taxonomy-deleted="handleTaxonomyDeleted" :modal="deleteTaxonomyModal" :taxonomy_id="taxonomy.id" />
</template>