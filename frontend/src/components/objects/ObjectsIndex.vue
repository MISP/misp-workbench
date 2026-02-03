<script setup>
import { ref } from "vue";
import { storeToRefs } from "pinia";
import { useObjectsStore } from "@/stores";
import { Modal } from "bootstrap";
import ObjectAttributesList from "@/components/objects/ObjectAttributesList.vue";
import ObjectActions from "@/components/objects/ObjectActions.vue";
import AddObjectModal from "@/components/objects/AddObjectModal.vue";
import DeleteObjectModal from "@/components/objects/DeleteObjectModal.vue";
import Paginate from "vuejs-paginate-next";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faSpinner } from "@fortawesome/free-solid-svg-icons";

const props = defineProps(["event_uuid", "page_size"]);

const objectsStore = useObjectsStore();
const { objects, pages, status } = storeToRefs(objectsStore);

function onPageChange(page) {
  objectsStore.get({
    page: page,
    size: props.page_size,
    event_uuid: props.event_uuid,
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
  <div v-if="status.error" class="text-danger">
    Error loading objects: {{ status.error }}
  </div>
  <span v-if="status.loading">
    <FontAwesomeIcon :icon="faSpinner" spin class="ms-2" />
  </span>
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
    v-if="pages > 1"
    :page-count="pages"
    :click-handler="onPageChange"
  />
  <AddObjectModal
    id="addObjectModal"
    :modal="addObjectModal"
    :event_uuid="event_uuid"
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
