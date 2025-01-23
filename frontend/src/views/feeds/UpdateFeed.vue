<script setup>
import { storeToRefs } from "pinia";
import { useFeedsStore } from "@/stores";
import { useRoute } from "vue-router";
import UpdateFeed from "@/components/feeds/UpdateFeed.vue";
import Spinner from "@/components/misc/Spinner.vue";
const route = useRoute();
const feedsStore = useFeedsStore();
const { feed, status } = storeToRefs(feedsStore);
feedsStore.getById(route.params.id);
defineProps(["id"]);
</script>

<template>
  <Spinner v-if="status.loading" />
  <UpdateFeed v-if="!status.loading" :feed="feed" :status="status" />
  <div v-if="status.error" class="text-danger">
    Error loading feed: {{ status.error }}
  </div>
</template>
