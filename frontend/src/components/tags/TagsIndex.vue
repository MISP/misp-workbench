<script setup>
import Badge from "@/components/misc/Badge.vue";

defineProps({
  tags: {
    type: Array,
    required: true,
  },
});
</script>

<style scoped>
.tag {
  float: left;
  margin: 0.1em;
}
</style>

<template>
  <div class="d-flex flex-wrap overflow-auto" style="max-height: 200px">
    <Badge
      v-for="tag in tags"
      :key="tag.name || tag.Tag.name"
      :value="tag.name || tag.Tag.name"
      :colour="tag.colour || tag.Tag.colour"
    />
  </div>
</template>

<style scoped>
.badge {
  padding: 0.5em 1em;
}
</style>
