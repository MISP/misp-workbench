<script setup>
import { ref } from "vue";
import { storeToRefs } from "pinia";
import { useObjectsStore } from "@/stores";
import { Modal } from "bootstrap";
import ObjectAttributesList from "@/components/objects/ObjectAttributesList.vue";
import ObjectActions from "@/components/objects/ObjectActions.vue";
import AddObjectModal from "@/components/objects/AddObjectModal.vue";
import DeleteObjectModal from "@/components/objects/DeleteObjectModal.vue";
import Spinner from "@/components/misc/Spinner.vue";
import Paginate from "vuejs-paginate-next";

const props = defineProps(["event_id", "total_size", "page_size"]);
const page_count = Math.ceil(props.total_size / props.page_size);

const objectsStore = useObjectsStore();
const { objects, status } = storeToRefs(objectsStore);

function onPageChange(page) {
  objectsStore.get({
    page: page,
    size: props.page_size,
    event_id: props.event_id,
    deleted: false,
  });
}
onPageChange(1);

const addObjectModal = ref(null);
const deleteObjectModal = ref(null);
const selectedObject = ref(null);

function handleObjectsUpdated() {
  // TODO FIXME: resets the page to 1 and reloads the objects, not the best way to do this, reload current page
  onPageChange(1);
}

function openAddObjectModal() {
  addObjectModal.value = new Modal(document.getElementById("addObjectModal"));
  addObjectModal.value.show();
}
</script>

<template>
  <Spinner v-if="status.loading" />
  <div v-if="status.error" class="text-danger">
    Error loading objects: {{ status.error }}
  </div>
  <div class="table-responsive-sm">
    <div class="mt-2" :key="object.id" v-for="object in objects.items">
      <div class="card" v-if="!object.deleted">
        <div class="card-header">
          {{ object.name }}
          <ObjectActions
            :object="object"
            @object-deleted="handleObjectsUpdated"
          />
        </div>
        <div class="card-body">
          <ObjectAttributesList
            :attributes="object.attributes"
            :object_id="object.id"
            @attribute-enriched="handleObjectsUpdated"
          />
        </div>
      </div>
    </div>
  </div>
  <Paginate
    v-if="page_count > 1"
    :page-count="page_count"
    :click-handler="onPageChange"
  />
  <AddObjectModal
    id="addObjectModal"
    :modal="addObjectModal"
    :event_id="event_id"
    @object-created="handleObjectsUpdated"
  />
  <DeleteObjectModal
    id="deleteObjectModal"
    :modal="deleteObjectModal"
    :object="selectedObject"
    @object-deleted="handleObjectsUpdated"
  />
  <div class="mt-3">
    <button
      type="button"
      class="w-100 btn btn-outline-primary"
      @click="openAddObjectModal"
    >
      Add Object
    </button>
  </div>
</template>
