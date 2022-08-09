<script setup>
import { storeToRefs } from "pinia";
import { useOrganisationsStore } from "@/stores";
import { RouterLink } from "vue-router";
import Spinner from "@/components/misc/Spinner.vue";
const organisationsStore = useOrganisationsStore();
const { organisations } = storeToRefs(organisationsStore);
organisationsStore.getAll();
</script>

<template>
    <Spinner v-if="organisations.loading" />
    <div v-if="organisations.error" class="text-danger">
        Error loading organisations: {{ organisations.error }}
    </div>
    <div class="table-responsive-sm">
        <table v-if="!organisations.loading" class="table table-striped">
            <thead>
                <tr>
                    <th scope="col">id</th>
                    <th scope="col">name</th>
                    <th scope="col" class="d-none d-sm-table-cell">uuid</th>
                    <th scope="col" class="d-none d-sm-table-cell">nationality</th>
                    <th scope="col" class="d-none d-sm-table-cell">sector</th>
                    <th scope="col" class="d-none d-sm-table-cell">type</th>
                    <th scope="col" class="text-end">actions</th>
                </tr>
            </thead>
            <tbody>
                <tr :key="organisation.id" v-for="organisation in organisations">
                    <td>
                        <RouterLink :to="`/organisations/${organisation.id}`">{{ organisation.id }}</RouterLink>
                    </td>
                    <td class="text-start">{{ organisation.name }}</td>
                    <td class="d-none d-sm-table-cell">{{ organisation.uuid }}</td>
                    <td class="d-none d-sm-table-cell">{{ organisation.nationality }}</td>
                    <td class="d-none d-sm-table-cell">{{ organisation.sector }}</td>
                    <td class="d-none d-sm-table-cell">{{ organisation.type }}</td>
                    <td class="text-end">
                        <div class="flex-wrap" :class="{ 'btn-group-vertical': $isMobile, 'btn-group': !$isMobile }"
                            aria-label="Event Actions">
                            <RouterLink :to="`/organisations/delete/${organisation.id}`" tag="button"
                                class="btn btn-danger disabled">
                                <font-awesome-icon icon="fa-solid fa-trash" />
                            </RouterLink>
                            <RouterLink :to="`/organisations/update/${organisation.id}`" tag="button"
                                class="btn btn-primary disabled">
                                <font-awesome-icon icon="fa-solid fa-pen" />
                            </RouterLink>
                            <RouterLink :to="`/organisations/${organisation.id}`" tag="button" class="btn btn-primary">
                                <font-awesome-icon icon="fa-solid fa-eye" />
                            </RouterLink>
                        </div>
                    </td>
                </tr>
            </tbody>
        </table>
    </div>
</template>