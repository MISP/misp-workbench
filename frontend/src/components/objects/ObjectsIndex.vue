<script setup>
import { RouterLink } from "vue-router";
import { storeToRefs } from 'pinia'
import { useObjectsStore } from "@/stores";
import ObjectAttributesList from "@/components/objects/ObjectAttributesList.vue";
import AddObjectModal from "@/components/objects/AddObjectModal.vue";
import Spinner from "@/components/misc/Spinner.vue";
import Paginate from "vuejs-paginate-next";

const props = defineProps(['event_id', 'total_size', 'page_size']);
let page_count = Math.ceil(props.total_size / props.page_size);

const objectsStore = useObjectsStore();
const { objects, status } = storeToRefs(objectsStore);

function onPageChange(page) {
    objectsStore.get({
        skip: (page - 1) * props.page_size,
        limit: props.page_size,
        event_id: props.event_id
    });
}
onPageChange(1);

function handleObjectsUpdated(event) {
    // TODO FIXME: resets the page to 1 and reloads the objects, not the best way to do this, reload current page
    onPageChange(1);
}
</script>

<template>
    <Spinner v-if="status.loading" />
    <div v-if="status.error" class="text-danger">
        Error loading objects: {{ status.error }}
    </div>
    <div class="table-responsive-sm">
        <div class="mt-2" :key="object.id" v-for="object in objects">
            <div class="card">
                <div class="card-header">
                    {{ object.name }}
                </div>
                <div class="card-body">
                    <ObjectAttributesList :attributes="object.attributes" :object_id="object.id" />
                </div>
            </div>
        </div>
    </div>
    <Paginate v-if="page_count > 1" :page-count="page_count" :click-handler="onPageChange" />
    <AddObjectModal @object-created="handleObjectsUpdated" :event_id="event_id" />
    <div class="mt-3">
        <button type="button" class="w-100 btn btn-outline-primary" data-bs-toggle="modal"
            data-bs-target="#addObjectModal">Add Object</button>
    </div>
</template>