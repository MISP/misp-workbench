<script setup>
import { ref, onMounted } from 'vue';
import { Modal } from 'bootstrap';
import { storeToRefs } from 'pinia'
import { useFeedsStore } from "@/stores";
import DeleteFeedModal from "@/components/feeds/DeleteFeedModal.vue";

const props = defineProps(['feed']);
const emit = defineEmits(['feed-deleted']);

const deleteFeedModal = ref(null);
const feedsStore = useFeedsStore();

const showToast = ref(false);
const toastMessage = ref("");
const toastType = ref("text-bg-info");

onMounted(() => {
    deleteFeedModal.value = new Modal(document.getElementById(`deleteFeedModal_${props.feed.id}`));
});

function openDeleteFeedModal() {
    deleteFeedModal.value.show();
}

function handleFeedDeleted() {
    emit('feed-deleted', props.feed.id);
}

function fetchFeed(feed) {
    feedsStore.fetch(feed.id)
        .then((response) => {
            console.log('Feed fetched');
            console.log(response);
            toastMessage.value = "Feed fetch enqueued. Task ID: " + response.task.id;
            toastType.value = "text-bg-success";
            showToast.value = true;
        })
        .catch((error) => {
            console.log('Error fetching feed');
            console.log(error);
            toastType.value = "text-bg-error";
            toastMessage.value = "Error fetching feed: " + error;
        });
}

const hideToast = () => {
    showToast.value = false;
};

</script>

<style scoped>
.btn-toolbar {
    flex-wrap: nowrap !important;
}
</style>

<template>
    <div>
        <div class="toast-container position-fixed bottom-0 end-0 p-3">
            <div v-if="showToast" class="toast align-items-center border-0 show" :class="toastType" role="alert"
                aria-live="assertive" aria-atomic="true">
                <div class="d-flex">
                    <div class="toast-body">
                        {{ toastMessage }}
                    </div>
                    <button type="button" class="btn-close me-2 m-auto" @click="hideToast" aria-label="Close"></button>
                </div>
            </div>
        </div>
        <div class="btn-toolbar float-end" role="toolbar">
            <div class="flex-wrap btn-group me-2" aria-label="Sync Actions">
                <button type="button" class="btn btn-outline-primary" data-placement="top" title="Fetch"
                    @click="fetchFeed(feed)" :class="{ 'disabled': !feed.enabled }">
                    <font-awesome-icon icon="fa-solid fa-download" />
                </button>
                <button type="button" class="btn btn-outline-primary" data-toggle="tooltip" data-placement="top"
                    title="Preview">
                    <font-awesome-icon icon="fa-solid fa-magnifying-glass" />
                </button>
            </div>
            <div :class="{ 'btn-group-vertical': $isMobile, 'btn-group me-2': !$isMobile }" role="group"
                aria-label="Feed Actions">
                <RouterLink :to="`/feeds/${feed.id}`" tag="button" class="btn btn-outline-primary">
                    <font-awesome-icon icon="fa-solid fa-eye" />
                </RouterLink>
                <RouterLink :to="`/feeds/update/${feed.id}`" tag="button" class="btn btn-outline-primary">
                    <font-awesome-icon icon="fa-solid fa-pen" />
                </RouterLink>
            </div>
            <div class="btn-group me-2" role="group">
                <button type="button" class="btn btn-danger" @click="openDeleteFeedModal">
                    <font-awesome-icon icon="fa-solid fa-trash" />
                </button>
            </div>
        </div>
        <DeleteFeedModal :key="feed.id" :id="`deleteFeedModal_${feed.id}`" @feed-deleted="handleFeedDeleted"
            :modal="deleteFeedModal" :feed_id="feed.id" />
    </div>
</template>