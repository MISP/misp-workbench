<script setup>
import Badge from "@/components/misc/Badge.vue";
import CopyToClipboard from "@/components/misc/CopyToClipboard.vue";
import Timestamp from "@/components/misc/Timestamp.vue";
import TagsIndex from "@/components/tags/TagsIndex.vue";
defineProps(["attribute"]);
</script>

<template>
  <div class="card mb-2">
    <div class="card-header">
      <a :href="`/attributes/${attribute._source.uuid}`">
        {{ attribute._source.uuid }}
      </a>
    </div>
    <div class="card-body">
      <p class="card-text text-truncate">
        <TagsIndex :tags="attribute._source.tags" />
      </p>
      <p class="card-text">
        <Badge :value="attribute._source.type" />
        {{ attribute._source.value }}
        <CopyToClipboard :value="attribute._source.value" />
      </p>
    </div>
    <div class="card-footer text-muted">
      <Timestamp :timestamp="attribute._source.timestamp" />
    </div>
  </div>
</template>
