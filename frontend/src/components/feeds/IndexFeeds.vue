<script setup>
import { storeToRefs } from "pinia";
import { RouterLink } from "vue-router";
import Spinner from "@/components/misc/Spinner.vue";
import { useFeedsStore } from "@/stores";
import DeleteFeedModal from "@/components/feeds/DeleteFeedModal.vue";

const feedsStore = useFeedsStore();
const { feeds, status } = storeToRefs(feedsStore);

feedsStore.getAll();

function handleFeedDeleted(event) {
    feedsStore.getAll();
}

function toggleEnable(feed) {
    feed.enabled = !feed.enabled;
    // feed.testingConnection = true;
    // feedsStore
    //     .testConnection(feed.id)
    //     .then((response) => {
    //         if (response.status == "ok") {
    //             feed.connectionSucceeded = true;
    //         } else {
    //             feed.connectionSucceeded = false;
    //             feed.connectionFailed = true;
    //             feed.connectionError = response.error;
    //         }
    //         feed.testingConnection = false;
    //     })
    //     .catch((error) => {
    //         feed.connectionSucceeded = false;
    //         setErrors({ apiError: error });
    //     })
    //     .finally(() => { feed.testingConnection = false; });
}

function fetchFeed(feed) {
    feedsStore.fetch(feed.id);
}
</script>

<template>
    <Spinner v-if="status.loading" />
    <div class="table-responsive-sm">
        <table v-show="!status.loading" class="table table-striped text-start">
            <thead>
                <tr>
                    <th scope="col">id</th>
                    <th scope="col">name</th>
                    <th scope="col">provider</th>
                    <th scope="col" v-if="!$isMobile">url</th>
                    <th scope="col" v-if="!$isMobile">source_format</th>
                    <th scope="col" v-if="!$isMobile">input_source</th>
                    <th scope="col" class="text-end">enabled</th>
                    <th scope="col" class="text-end">actions</th>
                </tr>
            </thead>
            <tbody>
                <tr :key="feed.id" v-for="feed in feeds">
                    <td>
                        <RouterLink :to="`/feeds/${feed.id}`">{{ feed.id }}</RouterLink>
                    </td>
                    <td>{{ feed.name }}</td>
                    <td>{{ feed.provider }}</td>
                    <td v-if="!$isMobile">{{ feed.url }}</td>
                    <td v-if="!$isMobile">{{ feed.source_format }}</td>
                    <td v-if="!$isMobile">{{ feed.input_source }}</td>
                    <td class="text-end">
                        <div class="flex-wrap btn-group me-2" aria-label="Sync Actions">
                            <button type="button" class="btn" @click="toggleEnable(feed)"
                                :class="{ 'btn-outline-success': feed.enabled, 'btn-outline-danger': !feed.enabled }"
                                data-toggle="tooltip" data-placement="top" title="Toggle feed">
                                <font-awesome-icon v-if="feed.enabled" icon="fa-solid fa-check" />
                                <font-awesome-icon v-if="!feed.enabled" icon="fa-solid fa-xmark" />
                            </button>
                        </div>

                    </td>
                    <td class="text-end">
                        <div class="btn-toolbar float-end" role="toolbar">
                            <div class="flex-wrap btn-group me-2" aria-label="Sync Actions">
                                <button type="button" class="btn btn-outline-primary" data-placement="top" title="Fetch"
                                    @click="fetchFeed(feed)">
                                    <font-awesome-icon icon="fa-solid fa-download" />
                                </button>
                                <button type="button" class="btn btn-outline-primary" data-toggle="tooltip"
                                    data-placement="top" title="Preview">
                                    <font-awesome-icon icon="fa-solid fa-magnifying-glass" />
                                </button>
                                <RouterLink :to="`/feeds/configure/${feed.id}`" tag="button" title="Configure"
                                    class="btn btn-outline-primary">
                                    <font-awesome-icon icon="fa-solid fa-cog" />
                                </RouterLink>
                            </div>
                            <div class="flex-wrap"
                                :class="{ 'btn-group-vertical': $isMobile, 'btn-group me-2': !$isMobile }"
                                aria-label="Feed Actions">
                                <RouterLink :to="`/feeds/update/${feed.id}`" tag="button"
                                    class="btn btn-outline-primary">
                                    <font-awesome-icon icon="fa-solid fa-pen" />
                                </RouterLink>
                                <RouterLink :to="`/feeds/${feed.id}`" tag="button" class="btn btn-outline-primary">
                                    <font-awesome-icon icon="fa-solid fa-eye" />
                                </RouterLink>
                            </div>
                            <div class="btn-group me-2" role="group">
                                <button type="button" class="btn btn-danger" data-bs-toggle="modal"
                                    :data-bs-target="'#deleteFeedModal-' + feed.id">
                                    <font-awesome-icon icon="fa-solid fa-trash" />
                                </button>
                            </div>
                        </div>
                    </td>
                    <DeleteFeedModal @feed-deleted="handleFeedDeleted" :feed_id="feed.id" />
                </tr>
            </tbody>
        </table>
        <div v-if="status.error" class="alert alert-danger" role="alert">
            {{ status.error }}
        </div>
    </div>
</template>