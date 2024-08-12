<script setup>

import { useFeedsStore } from "@/stores";
import { storeToRefs } from 'pinia'
import * as Yup from "yup";

const feedsStore = useFeedsStore();
const { status } = storeToRefs(feedsStore);

const props = defineProps(['feed_id']);
const emit = defineEmits(['feed-deleted']);

function onSubmit() {
    return feedsStore
        .delete(props.feed_id)
        .then((response) => {
            emit('feed-deleted', { "feed_id": props.feed_id });
            document.getElementById('closeModalButton').click();
        })
        .catch((error) => status.error = error);
}
</script>

<template>
    <div :id="'deleteFeedModal-' + feed_id" class="modal fade" tabindex="-1" aria-labelledby="deleteFeedModal"
        aria-hidden="true">
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title" id="deleteFeedModal">Delete Feed #{{ feed_id }}</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Discard"></button>
                </div>
                <div class="modal-body">
                    Are you sure you want to delete this feed?
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
