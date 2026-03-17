<script setup>
import { computed } from "vue";
import { storeToRefs } from "pinia";
import { useFeedsStore } from "@/stores";
import EditFeedMISP from "@/components/feeds/misp/EditFeedMISP.vue";
import EditFeedLegacy from "@/components/feeds/EditFeedLegacy.vue";

const feedsStore = useFeedsStore();
const { feed } = storeToRefs(feedsStore);

const editComponent = computed(() => {
  switch (feed.value.source_format) {
    case "misp":
      return EditFeedMISP;
    default:
      return EditFeedLegacy;
  }
});
</script>

<template>
  <component :is="editComponent" />
</template>
