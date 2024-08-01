<script setup>
import { ref, onMounted } from 'vue';
import { Modal } from 'bootstrap';
import DeleteAttributeModal from "@/components/attributes/DeleteAttributeModal.vue";

const props = defineProps(['attribute']);
const emit = defineEmits(['attribute-deleted']);

const deleteAttributeModal = ref(null);

onMounted(() => {
    deleteAttributeModal.value = new Modal(document.getElementById(`deleteAttributeModal_${props.attribute.id}`));
});

function openDeleteAttributeModal() {
    deleteAttributeModal.value.show();
}

function handleAttributeDeleted() {
    emit('attribute-deleted', props.attribute.id);
}

</script>

<template>
    <div :class="{ 'btn-group-vertical': $isMobile, 'btn-group': !$isMobile }" aria-label="Attribute Actions">
        <RouterLink :to="`/attributes/${attribute.id}`" tag="button" class="btn btn-outline-primary">
            <font-awesome-icon icon="fa-solid fa-eye" />
        </RouterLink>
        <RouterLink :to="`/attributes/enrich/${attribute.id}`" tag="button" class="btn btn-outline-primary">
            <font-awesome-icon icon="fa-solid fa-magic-wand-sparkles" />
        </RouterLink>
        <RouterLink :to="`/attributes/update/${attribute.id}`" tag="button" class="btn btn-outline-primary">
            <font-awesome-icon icon="fa-solid fa-pen" />
        </RouterLink>
        <button type="button" class="btn btn-danger" @click="openDeleteAttributeModal">
            <font-awesome-icon icon="fa-solid fa-trash" />
        </button>
    </div>
    <DeleteAttributeModal :id="`deleteAttributeModal_${attribute.id}`" @attribute-deleted="handleAttributeDeleted"
        :modal="deleteAttributeModal" :attribute_id="attribute.id" />
</template>