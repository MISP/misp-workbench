<script setup>
import { useRouter } from "vue-router";
import UsersActions from "@/components/users/UsersActions.vue";
defineProps(["user_id", "user"]);
const router = useRouter();
function handleUserDeleted() {
  router.push(`/users`);
}
</script>

<template>
  <div class="card">
    <div class="card-header border-bottom">
      <div class="row">
        <div class="col-10">
          <h3>{{ user.email }}</h3>
        </div>
        <div class="col-2 text-end">
          <UsersActions
            :user="user"
            :default_actions="{ view: false }"
            @user-deleted="handleUserDeleted"
          />
        </div>
      </div>
    </div>
    <div class="card-body d-flex flex-column">
      <div class="table-responsive-sm">
        <table class="table table-striped">
          <tbody>
            <tr>
              <th>id</th>
              <td>{{ user.id }}</td>
            </tr>
            <tr>
              <th>email</th>
              <td>{{ user.email }}</td>
            </tr>
            <tr>
              <th>org_id</th>
              <td>{{ user.org_id }}</td>
            </tr>
            <tr>
              <th>role</th>
              <td v-if="user.role">{{ user.role.name }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
