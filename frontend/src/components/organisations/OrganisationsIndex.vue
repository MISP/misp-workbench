<script setup>
import { storeToRefs } from "pinia";
import { useOrganisationsStore } from "@/stores";
import { RouterLink } from "vue-router";
import Spinner from "@/components/misc/Spinner.vue";
import DeleteOrganisationModal from "@/components/organisations/DeleteOrganisationModal.vue";

const organisationsStore = useOrganisationsStore();
const { organisations, status } = storeToRefs(organisationsStore);

organisationsStore.getAll();

function handleOrganisationDeleted(event) {
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
              <div
                class="flex-wrap"
                :class="{
                  'btn-group-vertical': $isMobile,
                  'btn-group me-2': !$isMobile,
                }"
                aria-label="Organisation Actions"
              >
                <RouterLink
                  :to="`/organisations/${organisation.id}`"
                  class="btn btn-outline-primary"
                >
                  <font-awesome-icon icon="fa-solid fa-eye" />
                </RouterLink>
                <RouterLink
                  :to="`/organisations/update/${organisation.id}`"
                  class="btn btn-outline-primary"
                >
                  <font-awesome-icon icon="fa-solid fa-pen" />
                </RouterLink>
              </div>
              <div class="btn-group me-2" role="group">
                <button
                  type="button"
                  class="btn btn-danger"
                  data-bs-toggle="modal"
                  :data-bs-target="
                    '#deleteOrganisationModal-' + organisation.id
                  "
                >
                  <font-awesome-icon icon="fa-solid fa-trash" />
                </button>
              </div>
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
