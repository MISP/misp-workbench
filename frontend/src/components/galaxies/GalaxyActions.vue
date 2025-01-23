<script setup>
import { ref, onMounted } from "vue";
import { Modal } from "bootstrap";
import DeleteGalaxyModal from "@/components/galaxies/DeleteGalaxyModal.vue";

const props = defineProps(["galaxy"]);
const emit = defineEmits(["galaxy-deleted"]);

const deleteGalaxyModal = ref(null);

onMounted(() => {
  deleteGalaxyModal.value = new Modal(
    document.getElementById(`deleteGalaxyModal_${props.galaxy.id}`)
  );
});

function openDeleteGalaxyModal() {
  deleteGalaxyModal.value.show();
}

function handleGalaxyDeleted() {
  emit("galaxy-deleted", props.galaxy.id);
}
</script>

<style scoped>
.btn-toolbar {
  flex-wrap: nowrap !important;
}
</style>

<template>
  <div class="btn-toolbar float-end" role="toolbar">
    <div
      :class="{ 'btn-group-vertical': $isMobile, 'btn-group me-2': !$isMobile }"
      role="group"
      aria-label="Galaxy Actions"
    >
      <RouterLink
        :to="`/galaxies/${galaxy.id}`"
        tag="button"
        class="btn btn-outline-primary"
      >
        <font-awesome-icon icon="fa-solid fa-eye" />
      </RouterLink>
    </div>
    <div class="btn-group me-2" role="group">
      <button
        type="button"
        class="btn btn-danger"
        @click="openDeleteGalaxyModal"
      >
        <font-awesome-icon icon="fa-solid fa-trash" />
      </button>
    </div>
  </div>
  <DeleteGalaxyModal
    :key="galaxy.id"
    :id="`deleteGalaxyModal_${galaxy.id}`"
    @galaxy-deleted="handleGalaxyDeleted"
    :modal="deleteGalaxyModal"
    :galaxy_id="galaxy.id"
  />
</template>
