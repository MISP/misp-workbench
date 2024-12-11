<script setup>
import Badge from "@/components/misc/Badge.vue";
import { tagHelper } from "@/helpers";

defineProps(['tags']);


</script>

<style scoped>
.tag {
  float: left;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin: 0.1em;
}
</style>
<template>
  <div class="col-auto">
    <Badge v-for="tag in tags" :key="tag.name" :value="tag.name" :colour="tag.colour" />
  </div>
</template>

<script>
export default {
  props: {
    tags: {
      type: Array,
      required: true,
    },
  }
};
</script>

<style scoped>
.badge {
  padding: 0.5em 1em;
}
</style>