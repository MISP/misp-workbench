<script setup>
const emit = defineEmits(["prevPageClick", "nextPageClick", "setPageClick"]);
defineProps(["currentPage", "hasPrevPage", "hasNextPage", "totalPages"]);

function nextPageClick(event) {
  event.preventDefault();
  emit("nextPageClick");
}

function prevPageClick(event) {
  event.preventDefault();
  emit("prevPageClick");
}

function setPageClick(p) {
  emit("setPageClick", p);
}
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
          @click="prevPageClick($event)"
          :class="{ disabled: !hasPrevPage || currentPage === 1 }"
          >Previous</a
        >
      </li>
      <li class="page-item">
        <input
          type="number"
          class="form-control"
          style="width: 80px; display: inline-block"
          :value="currentPage"
          @change="(e) => setPageClick(e.target.value)"
        />
      </li>
      <li class="page-item">
        <a
          class="page-link"
          href="#"
          @click="nextPageClick($event)"
          :class="{ disabled: !hasNextPage || totalPages === currentPage }"
          >Next</a
        >
      </li>
    </ul>
    <div
      class="d-flex justify-content-between align-items-center mb-3 float-end"
      v-if="totalPages !== undefined"
    >
      <div>
        <small class="text-muted">total pages: {{ totalPages }}</small>
      </div>
    </div>
  </nav>
</template>
