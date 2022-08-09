<script setup>
defineProps(['organisation']);
</script>

<template>
    <div class="card">
        <div class="card-header border-bottom">
            <div class="row">
                <div class="col-10">
                    <h3>{{ organisation.name }}</h3>
                </div>
                <div class="col-2 text-end">
                    <div class="flex-wrap" :class="{ 'btn-group-vertical': $isMobile, 'btn-group': !$isMobile }"
                        aria-label="Organisation Actions">
                        <RouterLink :to="`/organisations/delete/${organisation.id}`" tag="button"
                            class="btn btn-danger disabled">
                            <font-awesome-icon icon="fa-solid fa-trash" />
                        </RouterLink>
                        <RouterLink :to="`/organisations/update/${organisation.id}`" tag="button"
                            class="btn btn-primary disabled">
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
                            <th scope="row">id</th>
                            <td>{{ organisation.id }}</td>
                        </tr>
                        <tr>
                            <th scope="row">uuid</th>
                            <td>{{ organisation.uuid }}
                                <font-awesome-icon class="text-primary" icon="fa-solid fa-copy" />
                            </td>
                        </tr>
                        <tr>
                            <th scope="row">description</th>
                            <td>{{ organisation.description }}</td>
                        </tr>
                        <tr>
                            <th scope="row">date_created</th>
                            <td>{{ organisation.date_created }}</td>
                        </tr>
                        <tr>
                            <th scope="row">date_modified</th>
                            <td>{{ organisation.date_modified }}</td>
                        </tr>
                        <tr>
                            <th scope="row">type</th>
                            <td>{{ organisation.type }}</td>
                        </tr>
                        <tr>
                            <th scope="row">nationality</th>
                            <td>{{ organisation.nationality }}</td>
                        </tr>
                        <tr>
                            <th scope="row">sector</th>
                            <td>{{ organisation.sector }}</td>
                        </tr>
                        <tr>
                            <th scope="row">created_by</th>
                            <td>{{ organisation.created_by }}</td>
                        </tr>
                        <tr>
                            <th scope="row">contacts</th>
                            <td>{{ organisation.contacts }}</td>
                        </tr>
                        <tr>
                            <th scope="row">local</th>
                            <td>{{ organisation.local }}</td>
                        </tr>
                        <tr>
                            <th scope="row">restricted_to_domain</th>
                            <td>{{ organisation.restricted_to_domain }}</td>
                        </tr>
                        <tr>
                            <th scope="row">landing_page</th>
                            <td>{{ organisation.landing_page }}</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</template>