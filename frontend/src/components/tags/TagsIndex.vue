<script setup>
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
    <span class="badge mx-1 tag" v-for="tag in tags" :key="tag.name"
      :style="{ backgroundColor: tag.colour, color: getContrastColor(tag.colour) }" :title="tag.name">
      {{ tag.name }}
    </span>
  </div>
</template>

<script>
export default {
  props: {
    tags: {
      type: Array,
      required: true,
    },
  },
  methods: {
    getContrastColor(hex) {
      hex = hex.replace("#", "");

      // Convert the hex color to RGB
      const r = parseInt(hex.substring(0, 2), 16);
      const g = parseInt(hex.substring(2, 4), 16);
      const b = parseInt(hex.substring(4, 6), 16);

      // Calculate the luminance
      const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;

      // If luminance is high, use black text; otherwise, use white text
      return luminance > 0.5 ? "#000000" : "#FFFFFF";
    },
  },
};
</script>

<style scoped>
.badge {
  padding: 0.5em 1em;
}
</style>