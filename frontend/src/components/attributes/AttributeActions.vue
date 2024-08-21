<script setup>
import { ref, onMounted } from 'vue';
import { Modal } from 'bootstrap';
import { storeToRefs } from 'pinia'
import { useModulesStore } from "@/stores";
import DeleteAttributeModal from "@/components/attributes/DeleteAttributeModal.vue";
import EnrichAttributeModal from "@/components/attributes/EnrichAttributeModal.vue";

const props = defineProps(['attribute']);
const emit = defineEmits(['attribute-created', 'attribute-updated', 'attribute-deleted', 'object-created', 'attribute-enriched']);

const deleteAttributeModal = ref(null);
const enrichAttributeModal = ref(null);
const modulesStore = useModulesStore();
const { modulesResponses } = storeToRefs(modulesStore);

onMounted(() => {
    deleteAttributeModal.value = new Modal(document.getElementById(`deleteAttributeModal_${props.attribute.id}`));
    enrichAttributeModal.value = new Modal(document.getElementById(`enrichAttributeModal_${props.attribute.id}`));
});

function openDeleteAttributeModal() {
    deleteAttributeModal.value.show();
}

function openEnrichAttributeModal() {
    modulesResponses.value = [];
    enrichAttributeModal.value.show();
}

function handleAttributeDeleted() {
    emit('attribute-deleted', props.attribute.id);
}

function handleAttributeEnriched() {
    emit('attribute-enriched', props.attribute.id);
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
            aria-label="Attribute Actions">
            <RouterLink :to="`/attributes/${attribute.id}`" tag="button" class="btn btn-outline-primary">
                <font-awesome-icon icon="fa-solid fa-eye" />
            </RouterLink>
            <button type="button" class="btn btn-outline-primary" @click="openEnrichAttributeModal">
                <font-awesome-icon icon="fa-solid fa-magic-wand-sparkles" />
            </button>
            <RouterLink :to="`/attributes/update/${attribute.id}`" tag="button" class="btn btn-outline-primary">
                <font-awesome-icon icon="fa-solid fa-pen" />
            </RouterLink>
        </div>
        <div class="btn-group me-2" role="group">
            <button type="button" class="btn btn-danger" @click="openDeleteAttributeModal">
                <font-awesome-icon icon="fa-solid fa-trash" />
            </button>
        </div>
    </div>
    <DeleteAttributeModal :key="attribute.id" :id="`deleteAttributeModal_${attribute.id}`"
        @attribute-deleted="handleAttributeDeleted" :modal="deleteAttributeModal" :attribute_id="attribute.id" />
    <EnrichAttributeModal :key="attribute.id" :id="`enrichAttributeModal_${attribute.id}`"
        @attribute-enriched="handleAttributeEnriched" :modal="enrichAttributeModal" :attribute="attribute" />
</template>