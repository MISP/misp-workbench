<script setup>
import DistributionLevel from "@/components/enums/DistributionLevel.vue";
import TagsIndex from "@/components/tags/TagsIndex.vue";
import { RouterLink } from "vue-router";

defineProps(['attributes']);
</script>

<template>
    <table class="table table-striped">
        <thead>
            <tr>
                <th style="width: 30%" scope="col">value</th>
                <th style="width: 30%" scope="col" class="d-none d-sm-table-cell">tags</th>
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
                <td class="d-none d-sm-table-cell">
                    <TagsIndex :tags="attribute.tags" />
                </td>
                <td class="d-none d-sm-table-cell">{{ attribute.category }}</td>
                <td>{{ attribute.type }}</td>
                <td class="d-none d-sm-table-cell">{{ attribute.timestamp }}</td>
                <td class="d-none d-sm-table-cell">
                    <DistributionLevel :distribution_level_id=attribute.distribution />
                </td>
                <td class="text-end">
                    <div class="flex-wrap btn-group-vertical" aria-label="Attribute Actions">
                        <RouterLink :to="`/attributes/delete/${attribute.id}`" tag="button"
                            class="btn btn-danger disabled">
                            <font-awesome-icon icon="fa-solid fa-trash" />
                        </RouterLink>
                        <RouterLink :to="`/attributes/update/${attribute.id}`" tag="button"
                            class="btn btn-primary disabled">
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
</template>