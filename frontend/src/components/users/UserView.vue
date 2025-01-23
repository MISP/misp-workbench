<script setup>
import DeleteUserModal from "@/components/users/DeleteUserModal.vue";
const props = defineProps(["user_id", "user"]);
function handleUserDeleted(event) {
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
          <div
            class="flex-wrap"
            :class="{
              'btn-group-vertical': $isMobile,
              'btn-group': !$isMobile,
            }"
            aria-label="User Actions"
          >
            <button
              type="button"
              class="btn btn-outline-danger"
              data-bs-toggle="modal"
              :data-bs-target="'#deleteUserModal-' + user.id"
            >
              <font-awesome-icon icon="fa-solid fa-trash" />
            </button>
            <RouterLink
              :to="`/users/update/${user.id}`"
              tag="button"
              class="btn btn-outline-primary"
            >
              <font-awesome-icon icon="fa-solid fa-pen" />
            </RouterLink>
          </div>
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
        <DeleteUserModal @user-deleted="handleUserDeleted" :user_id="user_id" />
      </div>
    </div>
  </div>
</template>
