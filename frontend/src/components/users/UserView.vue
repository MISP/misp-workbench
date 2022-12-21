<script setup>
defineProps(['user']);
</script>

<template>
    <div class="card">
        <div class="card-header border-bottom">
            <div class="row">
                <div class="col-10">
                    <h3>{{ user.email }}</h3>
                </div>
                <div class="col-2 text-end">
                    <div class="flex-wrap" :class="{ 'btn-group-vertical': $isMobile, 'btn-group': !$isMobile }"
                        aria-label="User Actions">
                        <RouterLink :to="`/users/delete/${user.id}`" tag="button" class="btn btn-danger disabled">
                            <font-awesome-icon icon="fa-solid fa-trash" />
                        </RouterLink>
                        <RouterLink :to="`/users/update/${user.id}`" tag="button" class="btn btn-primary disabled">
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
                            <td>{{ user.role.name }}</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</template>