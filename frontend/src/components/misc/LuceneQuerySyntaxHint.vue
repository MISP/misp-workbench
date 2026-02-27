<script setup>
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faFileLines } from "@fortawesome/free-solid-svg-icons";
import LuceneQuerySyntaxCheatsheet from "@/components/misc/LuceneQuerySyntaxCheatsheetModal.vue";
</script>

<template>
  <span
    class="text-muted fst-italic small d-flex align-items-center justify-content-center mt-1"
  >
    Lucene query syntax supported
    <button
      type="button"
      class="btn btn-sm d-flex align-items-center"
      data-bs-toggle="modal"
      data-bs-target="#luceneQuerySyntaxCheatsheetModal"
    >
      <FontAwesomeIcon :icon="faFileLines" class="ms-1 cursor-pointer" />
    </button>
  </span>
  <Teleport to="body">
    <LuceneQuerySyntaxCheatsheet />
  </Teleport>
</template>
