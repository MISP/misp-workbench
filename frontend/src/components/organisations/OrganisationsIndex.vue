<script setup>
import { storeToRefs } from "pinia";
import { useOrganisationsStore } from "@/stores";
import { RouterLink } from "vue-router";
import Spinner from "@/components/misc/Spinner.vue";
import DeleteOrganisationModal from "@/components/organisations/DeleteOrganisationModal.vue";
import OrganisationActions from "@/components/organisations/OrganisationActions.vue";

const organisationsStore = useOrganisationsStore();
const { organisations, status } = storeToRefs(organisationsStore);

organisationsStore.getAll();

function handleOrganisationDeleted() {
  organisationsStore.getAll();
}
</script>

<template>
  <Spinner v-if="status.loading" />
  <div v-if="status.error" class="text-danger">
    Error loading organisations: {{ status.error }}
  </div>
  <div class="table-responsive-sm">
    <table class="table table-striped">
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
            <RouterLink :to="`/organisations/${organisation.id}`">{{
              organisation.id
            }}</RouterLink>
          </td>
          <td class="text-start">{{ organisation.name }}</td>
          <td class="d-none d-sm-table-cell">{{ organisation.uuid }}</td>
          <td class="d-none d-sm-table-cell">{{ organisation.nationality }}</td>
          <td class="d-none d-sm-table-cell">{{ organisation.sector }}</td>
          <td class="d-none d-sm-table-cell">{{ organisation.type }}</td>
          <td class="text-end">
            <div class="btn-toolbar float-end" role="toolbar">
              <OrganisationActions :organisation_uuid="organisation.uuid" />
            </div>
          </td>
          <DeleteOrganisationModal
            @organisation-deleted="handleOrganisationDeleted"
            :organisation_id="organisation.id"
          />
        </tr>
      </tbody>
    </table>
  </div>
</template>
