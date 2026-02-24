<script setup>
import { storeToRefs } from "pinia";
import { useFeedsStore } from "@/stores";
import { useRoute } from "vue-router";
import FeedExplorer from "@/components/feeds/FeedExplorer.vue";
import Spinner from "@/components/misc/Spinner.vue";
import ApiError from "@/components/misc/ApiError.vue";

const route = useRoute();
const feedsStore = useFeedsStore();
const { feed, status } = storeToRefs(feedsStore);
feedsStore.getById(route.params.id);
defineProps(["id"]);
</script>

<template>
  <Spinner v-if="status.loading" />
  <FeedExplorer v-if="!status.loading && feed.id" :feed="feed" />
  <div
    v-if="status.error"
    class="w-100 alert alert-danger mt-3 mb-3 text-center"
  >
    <ApiError :errors="status.error" />
  </div>
</template>
