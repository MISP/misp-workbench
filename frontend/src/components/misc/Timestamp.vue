<script setup>
const props = defineProps(["timestamp"]);

// convert timestamp to human readable format
const timestamp = new Date(props.timestamp * 1000).toLocaleString();
</script>

<template>
  <span>{{ timestamp }} </span>
</template>
