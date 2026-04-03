<script setup>
import { storeToRefs } from "pinia";
import { RouterLink } from "vue-router";
import Spinner from "@/components/misc/Spinner.vue";
import UsersActions from "@/components/users/UsersActions.vue";
import { useUsersStore } from "@/stores";
const usersStore = useUsersStore();
const { users, status } = storeToRefs(usersStore);
usersStore.getAll();

function handleUserDeleted() {
  usersStore.getAll();
}
</script>

<template>
  <Spinner v-if="status.loading" />
  <div v-if="status.error" class="text-danger">
    Error loading users: {{ status.error }}
  </div>
  <div class="table-responsive-sm">
    <table class="table table-striped">
      <thead>
        <tr>
          <th scope="col">id</th>
          <th scope="col">email</th>
          <th scope="col">organisation</th>
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
          <td>
            <RouterLink :to="`/organisations/${user.organisation.uuid}`">
              {{ user.organisation.name }}
            </RouterLink>
          </td>
          <td>{{ !!user.disabled }}</td>
          <td class="text-end">
            <UsersActions :user="user" @user-deleted="handleUserDeleted" />
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
