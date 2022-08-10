<script setup>
import { storeToRefs } from "pinia";
import { RouterLink } from "vue-router";
import Spinner from "@/components/misc/Spinner.vue";
import { useUsersStore } from "@/stores";
const usersStore = useUsersStore();
const { users, status } = storeToRefs(usersStore);
usersStore.getAll();
</script>

<template>
    <Spinner v-if="status.loading" />
    <div v-if="status.error" class="text-danger">
        Error loading users: {{ status.error }}
    </div>
    <div class="table-responsive-sm">
        <table v-if="!status.loading" class="table table-striped">
            <thead>
                <tr>
                    <th scope="col">id</th>
                    <th scope="col">email</th>
                    <th scope="col">disabled</th>
                    <th scope="col" class="text-end">actions</th>
                </tr>
            </thead>
            <tbody>
                <tr :key="user.id" v-for="user in users">
                    <td>
                        <RouterLink :to="`/users/${user.id}`">{{ user.id }}</RouterLink>
                    </td>
                    <td>{{ user.email }}</td>
                    <td>{{ !!user.disabled }}</td>
                    <td class="text-end">
                        <div class="flex-wrap" :class="{ 'btn-group-vertical': $isMobile, 'btn-group': !$isMobile }"
                            aria-label="User Actions">
                            <RouterLink :to="`/users/delete/${user.id}`" tag="button" class="btn btn-danger disabled">
                                <font-awesome-icon icon="fa-solid fa-trash" />
                            </RouterLink>
                            <RouterLink :to="`/users/update/${user.id}`" tag="button" class="btn btn-primary disabled">
                                <font-awesome-icon icon="fa-solid fa-pen" />
                            </RouterLink>
                            <RouterLink :to="`/users/${user.id}`" tag="button" class="btn btn-primary">
                                <font-awesome-icon icon="fa-solid fa-eye" />
                            </RouterLink>
                        </div>
                    </td>
                </tr>
            </tbody>
        </table>
    </div>
</template>