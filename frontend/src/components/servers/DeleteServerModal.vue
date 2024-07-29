<script setup>

import { useServersStore } from "@/stores";
import { storeToRefs } from 'pinia'
import * as Yup from "yup";

const serversStore = useServersStore();
const { status } = storeToRefs(serversStore);

const props = defineProps(['server_id']);
const emit = defineEmits(['server-deleted']);

function onSubmit() {
    return serversStore
        .delete(props.server_id)
        .then((response) => {
            emit('server-deleted', { "server_id": props.server_id });
            document.getElementById('closeModalButton').click();
        })
        .catch((error) => status.error = error);
}
</script>

<template>
    <div :id="'deleteServerModal-' + server_id" class="modal fade" tabindex="-1" aria-labelledby="deleteServerModal"
        aria-hidden="true">
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title" id="deleteServerModal">Delete Server #{{ server_id }}</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Discard"></button>
                </div>
                <div class="modal-body">
                    Are you sure you want to delete this server?
                </div>
                <div v-if="status.error" class="w-100 alert alert-danger mt-3 mb-3">
                    {{ status.error }}
                </div>
                <div class="modal-footer">
                    <button id="closeModalButton" type="button" data-bs-dismiss="modal"
                        class="btn btn-secondary">Discard</button>
                    <button type="submit" @click="onSubmit" class="btn btn-outline-danger"
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
