<script setup>
import { ref, watch } from "vue";
import { storeToRefs } from "pinia";
import { useGalaxiesStore, useToastsStore } from "@/stores";
import Spinner from "@/components/misc/Spinner.vue";
import Paginate from "vuejs-paginate-next";
import GalaxyActions from "@/components/galaxies/GalaxyActions.vue";

const props = defineProps(["page_size"]);

const toastsStore = useToastsStore();
const galaxiesStore = useGalaxiesStore();
const { page_count, galaxies, status } = storeToRefs(galaxiesStore);
const searchTerm = ref("");

function onPageChange(page) {
  galaxiesStore.get({
    page: page,
    size: props.page_size,
    filter: searchTerm.value,
  });
}
onPageChange(1);

watch(searchTerm, () => {
  onPageChange(1);
});

function updateGalaxies() {
  galaxiesStore.update().then((response) => {
    toastsStore.push("Galaxy update enqueued. Task ID: " + response.task_id);
  });
}

function handleGalaxiesUpdated() {
  // TODO FIXME: resets the page to 1 and reloads the galaxies, not the best way to do this, reload current page
  onPageChange(1);
}

function toggle(property, galaxy) {
  galaxiesStore
    .toggle(property, galaxy)
    .then(() => {
      galaxy[property] = !galaxy[property];
    })
    .catch((errors) => (this.status.error = errors));
}
</script>

<template>
  <nav class="navbar position-relative pt-0">
    <div class="container-fluid">
      <div class="position-absolute top-50 start-50 translate-middle">
        <button
          type="button"
          class="btn btn-outline-primary"
          @click="updateGalaxies"
          :disabled="status.updating"
        >
          <span v-if="status.updating">
            <span
              class="spinner-border spinner-border-sm me-2"
              role="status"
              aria-hidden="true"
            ></span>
            Updating...
          </span>
          <span v-else>Update Galaxies</span>
        </button>
      </div>
      <form class="d-flex ms-auto" role="search">
        <div class="input-group">
          <span class="input-group-text">
            <font-awesome-icon icon="fa-solid fa-magnifying-glass" />
          </span>
          <input
            type="text"
            class="form-control"
            v-model="searchTerm"
            placeholder="Search"
          />
        </div>
      </form>
    </div>
  </nav>
  <div v-if="status.error" class="text-danger">
    Error loading galaxies: {{ status.error }}
  </div>
  <div class="table-responsive-sm">
    <table class="table table-striped">
      <thead>
        <tr>
          <th scope="col">name</th>
          <!-- <th scope="col">description</th> -->
          <th scope="col">version</th>
          <th scope="col">enabled</th>
          <th scope="col">local_only</th>
          <th scope="col">default</th>
          <th scope="col" width="20%" class="text-end">actions</th>
        </tr>
      </thead>
      <tbody>
        <tr :key="galaxy.uuid" v-for="galaxy in galaxies.items">
          <td class="text-start">
            <RouterLink :to="`/galaxies/${galaxy.uuid}`">{{
              galaxy.name
            }}</RouterLink>
          </td>
          <td>{{ galaxy.version }}</td>
          <td>
            <div class="flex-wrap btn-group me-2">
              <button
                type="button"
                class="btn"
                @click="toggle('enabled', galaxy)"
                :class="{
                  'btn-outline-success': galaxy.enabled,
                  'btn-outline-danger': !galaxy.enabled,
                }"
                data-toggle="tooltip"
                data-placement="top"
                title="Toggle galaxy"
              >
                <font-awesome-icon
                  v-if="galaxy.enabled"
                  icon="fa-solid fa-check"
                />
                <font-awesome-icon
                  v-if="!galaxy.enabled"
                  icon="fa-solid fa-xmark"
                />
              </button>
            </div>
          </td>
          <td>
            <div class="flex-wrap btn-group me-2">
              <button
                type="button"
                class="btn"
                @click="toggle('exclusive', galaxy)"
                :class="{
                  'btn-outline-success': galaxy.exclusive,
                  'btn-outline-danger': !galaxy.local_only,
                }"
                data-toggle="tooltip"
                data-placement="top"
                title="Toggle galaxy"
              >
                <font-awesome-icon
                  v-if="galaxy.exclusive"
                  icon="fa-solid fa-check"
                />
                <font-awesome-icon
                  v-if="!galaxy.exclusive"
                  icon="fa-solid fa-xmark"
                />
              </button>
            </div>
          </td>
          <td>
            <div class="flex-wrap btn-group me-2">
              <button
                type="button"
                class="btn"
                @click="toggle('required', galaxy)"
                :class="{
                  'btn-outline-success': galaxy.required,
                  'btn-outline-danger': !galaxy.default,
                }"
                data-toggle="tooltip"
                data-placement="top"
                title="Toggle galaxy"
              >
                <font-awesome-icon
                  v-if="galaxy.required"
                  icon="fa-solid fa-check"
                />
                <font-awesome-icon
                  v-if="!galaxy.required"
                  icon="fa-solid fa-xmark"
                />
              </button>
            </div>
          </td>
          <td>
            <GalaxyActions
              :galaxy="galaxy"
              @galaxy-deleted="handleGalaxiesUpdated"
            />
          </td>
        </tr>
      </tbody>
    </table>
  </div>
  <Paginate
    v-if="page_count > 1"
    :page-count="page_count"
    :click-handler="onPageChange"
  />
  <Spinner v-if="status.loading" />
</template>
