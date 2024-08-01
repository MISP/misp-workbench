<script setup>
import { RouterLink } from "vue-router";
import { storeToRefs } from 'pinia'
import { useAttributesStore } from "@/stores";
import DistributionLevel from "@/components/enums/DistributionLevel.vue";
import TagsIndex from "@/components/tags/TagsIndex.vue";
import Spinner from "@/components/misc/Spinner.vue";
import Paginate from "vuejs-paginate-next";
import AddAttributeModal from "@/components/attributes/AddAttributeModal.vue";
import DeleteAttributeModal from "@/components/attributes/DeleteAttributeModal.vue";
import Timestamp from "@/components/misc/Timestamp.vue";

const props = defineProps(['event_id', 'page_size']);
const attributesStore = useAttributesStore();
const { page_count, attributes, status } = storeToRefs(attributesStore);

function onPageChange(page) {
    attributesStore.get({
        page: page,
        size: props.page_size,
        event_id: props.event_id,
        deleted: false
    });
}
onPageChange(1);

function handleAttributesUpdated(event) {
    // TODO FIXME: resets the page to 1 and reloads the attributes, not the best way to do this, reload current page
    onPageChange(1);
}
</script>

<template>
    <div class="table-responsive-sm">
        <Spinner v-if="status.loading" />
        <div v-if="status.error" class="text-danger">
            Error loading attributes: {{ status.error }}
        </div>
        <table class="table table-striped">
            <thead>
                <tr>
                    <th style="width: 30%" scope="col">value</th>
                    <th style="width: 30%" scope="col" class="d-none d-sm-table-cell">tags</th>
                    <th style="width: 10%" scope="col">type</th>
                    <th style="width: 10%" scope="col" class="d-none d-sm-table-cell">timestamp</th>
                    <th style="width: 10%" scope="col" class="d-none d-sm-table-cell">distribution</th>
                    <th style="width: 10%" scope="col" class="text-end">actions</th>
                </tr>
            </thead>
            <tbody>
                <tr :key="attribute.id" v-for="attribute in attributes.items">
                    <td>{{ attribute.value }}</td>
                    <td class="d-none d-sm-table-cell">
                        <TagsIndex :tags="attribute.tags" />
                    </td>
                    <td>{{ attribute.type }}</td>
                    <td class="d-none d-sm-table-cell">
                        <Timestamp :timestamp="attribute.timestamp" />
                    </td>
                    <td class="d-none d-sm-table-cell">
                        <DistributionLevel :distribution_level_id=attribute.distribution />
                    </td>
                    <td class="text-end">
                        <div :class="{ 'btn-group-vertical': $isMobile, 'btn-group': !$isMobile }"
                            aria-label="Attribute Actions">
                            <RouterLink :to="`/attributes/${attribute.id}`" tag="button"
                                class="btn btn-outline-primary">
                                <font-awesome-icon icon="fa-solid fa-eye" />
                            </RouterLink>
                            <RouterLink :to="`/attributes/enrich/${attribute.id}`" tag="button"
                                class="btn btn-outline-primary">
                                <font-awesome-icon icon="fa-solid fa-magic-wand-sparkles" />
                            </RouterLink>
                            <RouterLink :to="`/attributes/update/${attribute.id}`" tag="button"
                                class="btn btn-outline-primary">
                                <font-awesome-icon icon="fa-solid fa-pen" />
                            </RouterLink>
                            <button type="button" class="btn btn-danger" data-bs-toggle="modal"
                                :data-bs-target="'#deleteAttributeModal-' + attribute.id">
                                <font-awesome-icon icon="fa-solid fa-trash" />
                            </button>
                        </div>
                    </td>
                    <DeleteAttributeModal @attribute-deleted="handleAttributesUpdated" :attribute_id="attribute.id" />
                </tr>
            </tbody>
        </table>
        <Paginate v-if="page_count > 1" :page-count="page_count" :click-handler="onPageChange" />
        <AddAttributeModal @attribute-created="handleAttributesUpdated" :event_id="event_id" />
        <div class="mt-3">
            <button type="button" class="w-100 btn btn-outline-primary" data-bs-toggle="modal"
                data-bs-target="#addAttributeModal">Add Attribute</button>
        </div>
    </div>
</template>