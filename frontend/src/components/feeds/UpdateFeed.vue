<script>
export default { inheritAttrs: false };
</script>

<script setup>
import { computed } from "vue";
import { storeToRefs } from "pinia";
import { useFeedsStore } from "@/stores";
import EditFeedMISP from "@/components/feeds/misp/EditFeedMISP.vue";
import EditFeedCsv from "@/components/feeds/csv/EditFeedCsv.vue";
import EditFeedLegacy from "@/components/feeds/EditFeedLegacy.vue";

const feedsStore = useFeedsStore();
const { feed } = storeToRefs(feedsStore);

const editComponent = computed(() => {
  switch (feed.value.source_format) {
    case "misp":
      return EditFeedMISP;
    case "csv":
      return EditFeedCsv;
    default:
      return EditFeedLegacy;
  }
});
</script>

<template>
  <component :is="editComponent" />
</template>
