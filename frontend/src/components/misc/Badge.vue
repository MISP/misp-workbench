<script setup>
import { tagHelper } from "@/helpers";
const props = defineProps({
  value: {
    type: String,
    required: true,
  },
  colour: {
    type: String,
    default: "#000000",
  },
  namespace: {
    type: String,
    default: "",
  },
});
</script>

<template>
  <span
    class="badge mx-1 tag"
    :style="{
      backgroundColor: tagHelper.getBackgroundColor(props.colour),
      color: tagHelper.getContrastColor(props.colour),
    }"
    :title="props.value"
  >
    {{ tagHelper.getTag(props.namespace, props.value) }}
  </span>
</template>
