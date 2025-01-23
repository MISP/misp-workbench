<script setup>
import { storeToRefs } from "pinia";
import { useFeedsStore } from "@/stores";
import { useRoute } from "vue-router";
import ViewFeed from "@/components/feeds/ViewFeed.vue";
import Spinner from "@/components/misc/Spinner.vue";
const route = useRoute();
const feedsStore = useFeedsStore();
const { feed, status } = storeToRefs(feedsStore);
feedsStore.getById(route.params.id);
defineProps(["id"]);
</script>

<template>
  <Spinner v-if="status.loading" />
  <ViewFeed v-show="!status.loading" :feed="feed" />
  <div v-if="status.error" class="text-danger">
    Error loading feed: {{ status.error }}
  </div>
</template>
