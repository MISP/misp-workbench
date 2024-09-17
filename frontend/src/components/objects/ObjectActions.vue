<script setup>
import { ref, onMounted } from 'vue';
import { Modal } from 'bootstrap';
import DeleteObjectModal from "@/components/objects/DeleteObjectModal.vue";

const props = defineProps(['object']);
const emit = defineEmits(['object-created', 'object-updated', 'object-deleted', 'object-created']);

const deleteObjectModal = ref(null);

onMounted(() => {
    deleteObjectModal.value = new Modal(document.getElementById(`deleteObjectModal_${props.object.id}`));
});

function openDeleteObjectModal() {
    deleteObjectModal.value.show();
}

function handleObjectDeleted() {
    emit('object-deleted', props.object.id);
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
            aria-label="Object Actions">
            <RouterLink :to="`/objects/update/${object.id}`" tag="button" class="btn btn-outline-primary">
                <font-awesome-icon icon="fa-solid fa-pen" />
            </RouterLink>
        </div>
        <div class="btn-group me-2" role="group">
            <button type="button" class="btn btn-danger" @click="openDeleteObjectModal">
                <font-awesome-icon icon="fa-solid fa-trash" />
            </button>
        </div>
    </div>
    <DeleteObjectModal :key="object.id" :id="`deleteObjectModal_${object.id}`" @object-deleted="handleObjectDeleted"
        :modal="deleteObjectModal" :object_id="object.id" />
</template>