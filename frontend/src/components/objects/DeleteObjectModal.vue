<script setup>
import { useObjectsStore } from "@/stores";
import { storeToRefs } from 'pinia'

const objectsStore = useObjectsStore();
const { status } = storeToRefs(objectsStore);

const props = defineProps(['object', 'modal']);
const emit = defineEmits(['object-deleted']);

function deleteObject() {
    return objectsStore
        .delete(props.object.id)
        .then((response) => {
            emit('object-deleted', { "object": props.object.id });
            props.modal.hide();
        })
        .catch((error) => status.error = error);
}
</script>

<template>
    <div id="deleteObjectModal" class="modal" aria-labelledby="deleteObjectModal" aria-hidden="true">
        <div class="modal-dialog modal-lg">
            <div v-if="object" class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Delete Object #{{ object.id }}</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Discard"></button>
                </div>
                <div class="modal-body">
                    Are you sure you want to delete this object?
                </div>
                <div v-if="status.error" class="w-100 alert alert-danger mt-3 mb-3">
                    {{ status.error }}
                </div>
                <div class="modal-footer">
                    <button id="closeModalButton" type="button" data-bs-dismiss="modal"
                        class="btn btn-secondary">Discard</button>
                    <button type="submit" @click="deleteObject" class="btn btn-outline-danger"
                        :class="{ 'disabled': status.loading }">
                        <span v-if="status.loading">
                            <span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
                        </span>
                        <span v-if="!status.loading">Delete</span>
                    </button>
                </div>
            </div>
        </div>
    </div>
</template>
