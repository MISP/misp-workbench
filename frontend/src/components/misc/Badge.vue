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
    class="badge mx-1 tag shadow-sm text-truncate"
    :style="{
      backgroundColor: tagHelper.getBackgroundColor(props.colour),
      color: tagHelper.getContrastColor(props.colour),
      maxWidth: 'calc(100% - 0.5rem)',
    }"
    :title="props.value"
  >
    {{ tagHelper.getTag(props.namespace, props.value) }}
  </span>
</template>
