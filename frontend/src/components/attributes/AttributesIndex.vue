<script setup>
import { RouterLink } from "vue-router";
import { storeToRefs } from 'pinia'
import { useAttributesStore } from "@/stores";
import DistributionLevel from "@/components/enums/DistributionLevel.vue";
import Spinner from "@/components/misc/Spinner.vue";
import Paginate from "vuejs-paginate-next";

const props = defineProps(['event_id', 'total_size', 'page_size']);
let page_count = Math.ceil(props.total_size / props.page_size);

const attributesStore = useAttributesStore();
const { attributes } = storeToRefs(attributesStore);

function onPageChange(page) {
    attributesStore.get({
        skip: (page - 1) * props.page_size,
        limit: props.page_size,
        event_id: props.event_id
    });
}
onPageChange(1);
</script>

<template>
    <div class="table-responsive-sm">
        <Spinner v-if="attributes.loading" />
        <div v-if="attributes.error" class="text-danger">
            Error loading attributes: {{ attributes.error }}
        </div>
        <table class="table table-striped">
            <thead>
                <tr>
                    <th style="width: 30%" scope="col">value</th>
                    <th style="width: 10%" scope="col" class="d-none d-sm-table-cell">category</th>
                    <th style="width: 10%" scope="col">type</th>
                    <th style="width: 10%" scope="col" class="d-none d-sm-table-cell">timestamp</th>
                    <th style="width: 10%" scope="col" class="d-none d-sm-table-cell">distribution</th>
                    <th style="width: 10%" scope="col" class="text-end">actions</th>
                </tr>
            </thead>
            <tbody>
                <tr :key="attribute.id" v-for="attribute in attributes">
                    <td>{{ attribute.value }}</td>
                    <td class="d-none d-sm-table-cell">{{ attribute.category }}</td>
                    <td>{{ attribute.type }}</td>
                    <td class="d-none d-sm-table-cell">{{ attribute.timestamp }}</td>
                    <td class="d-none d-sm-table-cell">
                        <DistributionLevel :distribution_level_id=attribute.distribution />
                    </td>
                    <td class="text-end">
                        <div class="flex-wrap" :class="{ 'btn-group-vertical': $isMobile, 'btn-group': !$isMobile }"
                            aria-label="Attribute Actions">
                            <RouterLink :to="`/attributes/delete/${attribute.id}`" tag="button" class="btn btn-danger">
                                <font-awesome-icon icon="fa-solid fa-trash" />
                            </RouterLink>
                            <RouterLink :to="`/attributes/update/${attribute.id}`" tag="button" class="btn btn-primary">
                                <font-awesome-icon icon="fa-solid fa-pen" />
                            </RouterLink>
                            <RouterLink :to="`/attributes/${attribute.id}`" tag="button" class="btn btn-primary">
                                <font-awesome-icon icon="fa-solid fa-eye" />
                            </RouterLink>
                        </div>
                    </td>
                </tr>
            </tbody>
        </table>
        <Paginate v-if="page_count > 1" :page-count="page_count" :click-handler="onPageChange" />
    </div>
</template>