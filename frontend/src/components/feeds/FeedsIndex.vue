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

function testFeedConnection(feed) {
    feed.testingConnection = true;
    feedsStore
        .testConnection(feed.id)
        .then((response) => {
            if (response.status == "ok") {
                feed.connectionSucceeded = true;
            } else {
                feed.connectionSucceeded = false;
                feed.connectionFailed = true;
                feed.connectionError = response.error;
            }
            feed.testingConnection = false;
        })
        .catch((error) => {
            feed.connectionSucceeded = false;
            setErrors({ apiError: error });
        })
        .finally(() => { feed.testingConnection = false; });
}

function pullFeed(feed) {
    feedsStore.pull(feed.id);
}
</script>

<template>
    <Spinner v-if="status.loading" />
    <div class="table-responsive-sm">
        <table v-show="!status.loading" class="table table-striped">
            <thead>
                <tr>
                    <th scope="col">id</th>
                    <th scope="col">name</th>
                    <th scope="col" v-if="!$isMobile">url</th>
                    <th scope="col">enabled</th>
                    <th scope="col" class="float-end">sync actions</th>
                    <th scope="col" class="text-end">actions</th>
                </tr>
            </thead>
            <tbody>
                <tr :key="feed.id" v-for="feed in feeds">
                    <td>
                        <RouterLink :to="`/feeds/${feed.id}`">{{ feed.id }}</RouterLink>
                    </td>
                    <td>{{ feed.name }}</td>
                    <td v-if="!$isMobile">{{ feed.url }}</td>
                    <td>{{ feed.enabled }}</td>
                    <td>
                        <div class="btn-toolbar float-end" role="toolbar">
                            <div class="flex-wrap btn-group me-2" aria-label="Sync Actions">
                                <button
                                    v-if="!feed.testingConnection && !feed.connectionSucceeded && !feed.connectionFailed"
                                    type="button" class="btn btn-outline-primary" @click="testFeedConnection(feed)"
                                    data-toggle="tooltip" data-placement="top" title="Check connection">
                                    <font-awesome-icon icon="fa-solid fa-check" />
                                </button>
                                <button v-if="feed.testingConnection" type="button" class="btn btn-light">
                                    <font-awesome-icon icon="fa-solid fa-sync" spin />
                                </button>
                                <button v-if="feed.connectionSucceeded" type="button" class="btn btn-success"
                                    data-toggle="tooltip" data-placement="top" title="Connection succeed">
                                    <font-awesome-icon icon="fa-solid fa-check" />
                                </button>
                                <button
                                    v-if="!feed.testingConnection && feed.connectionFailed && !feed.connectionSucceeded"
                                    type="button" class="btn btn-danger" @click="testFeedConnection(feed)"
                                    data-toggle="tooltip" data-placement="top"
                                    :title="'Connection failed: ' + feed.connectionError">
                                    <font-awesome-icon icon="fa-solid fa-xmark" />
                                </button>
                                <button type="button" class="btn btn-outline-primary" data-placement="top" title="Fetch"
                                    @click="fetchFeed(feed)">
                                    <font-awesome-icon icon="fa-solid fa-arrow-down" />
                                </button>
                                <button type="button" class="btn btn-outline-primary" data-toggle="tooltip"
                                    data-placement="top" title="Preview">
                                    <font-awesome-icon icon="fa-solid fa-magnifying-glass" />
                                </button>
                            </div>
                            <div class="flex-wrap btn-group" aria-label="Sync Actions">
                                <RouterLink :to="`/feeds/configure/${feed.id}`" tag="button"
                                    class="btn btn-outline-primary">
                                    <font-awesome-icon icon="fa-solid fa-cog" />
                                </RouterLink>
                            </div>
                        </div>
                    </td>
                    <td class="text-end">
                        <div class="btn-toolbar float-end" role="toolbar">
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