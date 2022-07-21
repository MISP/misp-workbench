<script setup>
import { RouterLink } from "vue-router";
defineProps(['objects']);
</script>

<template>
    <div class="table-responsive-sm">
        <table class="table table-striped">
            <thead>
                <tr>
                    <th scope="col">id</th>
                    <th scope="col">value</th>
                    <th scope="col">date</th>
                    <th scope="col" class="d-none d-sm-table-cell">distribution</th>
                    <th scope="col" class="text-end">actions</th>
                </tr>
            </thead>
            <tbody>
                <tr :key="object.id" v-for="object in objects">
                    <td>
                        <RouterLink :to="`/objects/${object.id}`">{{ object.id }}</RouterLink>
                    </td>
                    <td>{{ object.value }}</td>
                    <td>{{ object.date }}</td>
                    <td class="d-none d-sm-table-cell">{{ object.distribution }}</td>
                    <td>
                        <div class="flex-wrap" :class="{ 'btn-group-vertical': $isMobile, 'btn-group': !$isMobile }"
                            aria-label="object Actions">
                            <RouterLink :to="`/objects/delete/${object.id}`" tag="button" class="btn btn-danger">
                                <font-awesome-icon icon="fa-solid fa-trash" />
                            </RouterLink>
                            <RouterLink :to="`/objects/update/${object.id}`" tag="button" class="btn btn-primary">
                                <font-awesome-icon icon="fa-solid fa-pen" />
                            </RouterLink>
                            <RouterLink :to="`/objects/${object.id}`" tag="button" class="btn btn-primary">
                                <font-awesome-icon icon="fa-solid fa-eye" />
                            </RouterLink>
                        </div>
                    </td>
                </tr>
            </tbody>
        </table>
    </div>
</template>