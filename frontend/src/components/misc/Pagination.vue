<script setup>
const emit = defineEmits(["prevPageClick", "nextPageClick"]);
defineProps(["currentPage", "hasPrevPage", "hasNextPage"]);
</script>

<style>
ul.pagination {
  margin-bottom: 0;
}
</style>

<template>
  <nav>
    <ul class="pagination justify-content-center">
      <li class="page-item">
        <a
          class="page-link"
          href="#"
          @click="emit('prevPageClick')"
          :class="{ disabled: !hasPrevPage }"
          >Previous</a
        >
      </li>
      <!-- <li class="page-item"><a class="page-link disabled" href="#"> Current Page: {{ currentPage }} </a></li> -->
      <li class="page-item">
        <a
          class="page-link"
          href="#"
          @click="emit('nextPageClick')"
          :class="{ disabled: !hasNextPage }"
          >Next</a
        >
      </li>
    </ul>
  </nav>
</template>
