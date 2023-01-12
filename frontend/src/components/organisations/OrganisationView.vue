<script setup>
import DeleteOrganisationModal from "@/components/organisations/DeleteOrganisationModal.vue";
import { router } from "@/router";

defineProps(['organisation']);

function handleOrganisationDeleted(event) {
    router.push(`/organisations`);
}
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
                        <button type="button" class="btn btn-danger" data-bs-toggle="modal"
                            :data-bs-target="'#deleteOrganisationModal-' + organisation.id">
                            <font-awesome-icon icon="fa-solid fa-trash" />
                        </button>
                        <RouterLink :to="`/organisations/update/${organisation.id}`" tag="button"
                            class="btn btn-primary">
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
                            <th style="width: 30%">id</th>
                            <td>{{ organisation.id }}</td>
                        </tr>
                        <tr>
                            <th style="width: 30%">uuid</th>
                            <td>{{ organisation.uuid }}
                                <font-awesome-icon class="text-primary" icon="fa-solid fa-copy" />
                            </td>
                        </tr>
                        <tr>
                            <th style="width: 30%">description</th>
                            <td>{{ organisation.description }}</td>
                        </tr>
                        <tr>
                            <th style="width: 30%">date_created</th>
                            <td>{{ organisation.date_created }}</td>
                        </tr>
                        <tr>
                            <th style="width: 30%">date_modified</th>
                            <td>{{ organisation.date_modified }}</td>
                        </tr>
                        <tr>
                            <th style="width: 30%">type</th>
                            <td>{{ organisation.type }}</td>
                        </tr>
                        <tr>
                            <th style="width: 30%">nationality</th>
                            <td>{{ organisation.nationality }}</td>
                        </tr>
                        <tr>
                            <th style="width: 30%">sector</th>
                            <td>{{ organisation.sector }}</td>
                        </tr>
                        <tr>
                            <th style="width: 30%">created_by</th>
                            <td>{{ organisation.created_by }}</td>
                        </tr>
                        <tr>
                            <th style="width: 30%">contacts</th>
                            <td>{{ organisation.contacts }}</td>
                        </tr>
                        <tr>
                            <th style="width: 30%">local</th>
                            <td>{{ organisation.local }}</td>
                        </tr>
                        <tr>
                            <th style="width: 30%">restricted_to_domain</th>
                            <td>{{ organisation.restricted_to_domain }}</td>
                        </tr>
                        <tr>
                            <th style="width: 30%">landing_page</th>
                            <td>{{ organisation.landing_page }}</td>
                        </tr>
                    </tbody>
                </table>
                <DeleteOrganisationModal @organisation-deleted="handleOrganisationDeleted"
                    :organisation_id="organisation.id" />
            </div>
        </div>
    </div>
</template>