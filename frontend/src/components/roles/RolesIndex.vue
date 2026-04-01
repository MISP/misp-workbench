<script setup>
import { storeToRefs } from "pinia";
import { useRolesStore } from "@/stores";
import Spinner from "@/components/misc/Spinner.vue";

const rolesStore = useRolesStore();
const { roles, status } = storeToRefs(rolesStore);

rolesStore.getAll();
</script>

<template>
  <Spinner v-if="status.loading" />
  <div v-if="status.error" class="text-danger">
    Error loading roles: {{ status.error }}
  </div>
  <div class="table-responsive-sm">
    <table class="table table-striped align-middle">
      <thead>
        <tr>
          <th scope="col">#</th>
          <th scope="col">name</th>
          <th scope="col">scopes</th>
          <th scope="col" class="text-center">default</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="role in roles" :key="role.id">
          <td class="text-muted" style="width: 3rem">{{ role.id }}</td>
          <td class="fw-semibold">{{ role.name }}</td>
          <td>
            <span v-if="role.scopes.includes('*')" class="badge bg-danger"
              >*</span
            >
            <template v-else>
              <span
                v-for="scope in role.scopes"
                :key="scope"
                class="badge me-1 mb-1"
                :class="{
                  'bg-primary': scope.endsWith(':*'),
                  'bg-secondary': !scope.endsWith(':*'),
                }"
                >{{ scope }}</span
              >
            </template>
          </td>
          <td class="text-center">
            <span v-if="role.default_role" class="badge bg-success">yes</span>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
