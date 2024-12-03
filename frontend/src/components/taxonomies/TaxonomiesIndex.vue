<script setup>
import { storeToRefs } from 'pinia'
import { useTaxonomiesStore } from "@/stores";
import Spinner from "@/components/misc/Spinner.vue";
import Paginate from "vuejs-paginate-next";

const props = defineProps(['page_size']);

const taxonomiesStore = useTaxonomiesStore();
const { page_count, taxonomies, status } = storeToRefs(taxonomiesStore);

function onPageChange(page) {
    taxonomiesStore.get({
        page: page,
        size: props.page_size
    });
}
onPageChange(1);

</script>

<template>
    <Spinner v-if="status.loading" />
    <div v-if="status.error" class="text-danger">
        Error loading taxonomies: {{ status.error }}
    </div>
    <div class="table-responsive-sm">
        <table class="table table-striped">
            <thead>
                <tr>
                    <th scope="col">id</th>
                    <th scope="col">namespace</th>
                    <!-- <th scope="col">description</th> -->
                    <th scope="col">version</th>
                    <th scope="col">enabled</th>
                    <th scope="col">required</th>
                    <th scope="col">highlighted</th>
                    <th scope="col">active tags</th>
                    <th scope="col" width="20%" class="text-end">actions</th>
                </tr>
            </thead>
            <tbody>
                <tr :key="taxonomy.id" v-for="taxonomy in taxonomies.items">
                    <td>
                        <RouterLink :to="`/taxonomies/${taxonomy.id}`">{{ taxonomy.id }}</RouterLink>
                    </td>
                    <td>{{ taxonomy.namespace }}</td>
                    <td>{{ taxonomy.version }}</td>
                    <td>{{ taxonomy.enabled }}</td>
                    <td>{{ taxonomy.required }}</td>
                    <td>{{ taxonomy.highlighted }}</td>
                    <td>-</td>
                    <td>-</td>
                </tr>
            </tbody>
        </table>
    </div>
    <Paginate v-if="page_count > 1" :page-count="page_count" :click-handler="onPageChange" />
</template>