<script setup>
import { RouterLink } from "vue-router";
defineProps(['attributes']);
</script>

<template>
    <div class="table-responsive-sm">
        <table class="table table-striped">
            <thead>
                <tr>
                    <th scope="col">id</th>
                    <th scope="col">value</th>
                    <th scope="col" class="d-none d-sm-table-cell">category</th>
                    <th scope="col">type</th>
                    <th scope="col" class="d-none d-sm-table-cell">timestamp</th>
                    <th scope="col" class="d-none d-sm-table-cell">distribution</th>
                    <th scope="col" class="text-end">actions</th>
                </tr>
            </thead>
            <tbody>
                <tr :key="attribute.id" v-for="attribute in attributes">
                    <td>
                        <RouterLink :to="`/attributes/${attribute.id}`">{{ attribute.id }}</RouterLink>
                    </td>
                    <td>{{ attribute.value }}</td>
                    <td class="d-none d-sm-table-cell">{{ attribute.category }}</td>
                    <td>{{ attribute.type }}</td>
                    <td class="d-none d-sm-table-cell">{{ attribute.timestamp }}</td>
                    <td class="d-none d-sm-table-cell">{{ attribute.distribution }}</td>
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
    </div>
</template>