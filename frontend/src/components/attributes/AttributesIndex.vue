<script setup>
import { ref, onMounted } from "vue";
import { storeToRefs } from 'pinia'
import { useAttributesStore } from "@/stores";
import DistributionLevel from "@/components/enums/DistributionLevel.vue";
import TagsSelect from "@/components/tags/TagsSelect.vue";
import Spinner from "@/components/misc/Spinner.vue";
import Paginate from "vuejs-paginate-next";
import AddAttributeModal from "@/components/attributes/AddAttributeModal.vue";
import AttributeActions from "@/components/attributes/AttributeActions.vue";
import CopyToClipboard from "@/components/misc/CopyToClipboard.vue";
import Timestamp from "@/components/misc/Timestamp.vue";
import { Modal } from 'bootstrap';

const props = defineProps(['event_id', 'page_size']);
const attributesStore = useAttributesStore();
const { page_count, attributes, status } = storeToRefs(attributesStore);

const addAttributeModal = ref(null);

onMounted(() => {
    addAttributeModal.value = new Modal(document.getElementById('addAttributeModal'));
});

function openAddAttributeModal() {
    addAttributeModal.value.show();
}

function onPageChange(page) {
    attributesStore.get({
        page: page,
        size: props.page_size,
        event_id: props.event_id,
    });
}
onPageChange(1);

function handleAttributesUpdated(event) {
    // TODO FIXME: resets the page to 1 and reloads the attributes, not the best way to do this, reload current page
    onPageChange(1);
}
</script>

<style scoped>
.table {
    table-layout: fixed;
}

.value {
    width: 30%;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 100%;
    box-sizing: border-box;
}
</style>

<template>
    <div class="table-responsive-sm">
        <div v-if="status.error" class="text-danger">
            Error loading attributes: {{ status.error }}
        </div>
        <table class="table table-striped">
            <thead>
                <tr>
                    <th scope="col">value</th>
                    <th style="width: 400px;" scope="col" class="d-none d-sm-table-cell">tags</th>
                    <th scope="col">type</th>
                    <th scope="col" class="d-none d-sm-table-cell">timestamp</th>
                    <th scope="col" class="d-none d-sm-table-cell">distribution</th>
                    <th scope="col" class="text-end">actions</th>
                </tr>
            </thead>
            <tbody>
                <tr :key="attribute.id" v-for="attribute in attributes.items">
                    <td class="value">
                        <CopyToClipboard :value="attribute.value" />
                        {{ attribute.value }}
                    </td>
                    <td class="d-none d-sm-table-cell">
                        <TagsSelect :modelClass="'attribute'" :model="attribute" :selectedTags="attribute.tags" />
                    </td>
                    <td>{{ attribute.type }}</td>
                    <td class="d-none d-sm-table-cell">
                        <Timestamp :timestamp="attribute.timestamp" />
                    </td>
                    <td class="d-none d-sm-table-cell">
                        <DistributionLevel :distribution_level_id=attribute.distribution />
                    </td>
                    <td class="text-end">
                        <AttributeActions :attribute="attribute" @attribute-deleted="handleAttributesUpdated" />
                    </td>
                </tr>
            </tbody>
        </table>
        <Spinner v-if="status.loading" />
        <Paginate v-if="page_count > 1" :page-count="page_count" :click-handler="onPageChange" />
        <AddAttributeModal id="addAttributeModal" @attribute-created="handleAttributesUpdated"
            :modal="addAttributeModal" :event_id="event_id" />
        <div class="mt-3">
            <button type="button" class="w-100 btn btn-outline-primary" @click="openAddAttributeModal">Add
                Attribute</button>
        </div>
    </div>
</template>