<script setup>
import { ref, watch } from "vue";
import { storeToRefs } from "pinia";
import { useTaxonomiesStore, useToastsStore } from "@/stores";
import Spinner from "@/components/misc/Spinner.vue";
import Paginate from "vuejs-paginate-next";
import TaxonomyActions from "@/components/taxonomies/TaxonomyActions.vue";

const props = defineProps(["page_size"]);

const toastsStore = useToastsStore();
const taxonomiesStore = useTaxonomiesStore();
const { page_count, taxonomies, status } = storeToRefs(taxonomiesStore);
const searchTerm = ref("");

function onPageChange(page) {
  taxonomiesStore.get({
    page: page,
    size: props.page_size,
    filter: searchTerm.value,
  });
}
onPageChange(1);

watch(searchTerm, () => {
  onPageChange(1);
});

function handleTaxonomiesUpdated() {
  // TODO FIXME: resets the page to 1 and reloads the taxonomies, not the best way to do this, reload current page
  onPageChange(1);
}

function toggle(property, taxonomy) {
  taxonomiesStore
    .toggle(property, taxonomy)
    .then(() => {
      taxonomy[property] = !taxonomy[property];
    })
    .catch((errors) => (this.status.error = errors));
}

function updateTaxonomies() {
  taxonomiesStore.update().then((response) => {
    toastsStore.push("Taxonomy update enqueued. Task ID: " + response.task_id);
  });
}
</script>

<template>
  <nav class="navbar position-relative pt-0">
    <div class="container-fluid">
      <div class="position-absolute top-50 start-50 translate-middle">
        <button
          type="button"
          class="btn btn-outline-primary"
          @click="updateTaxonomies"
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
          <span v-else>Update Taxonomies</span>
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
    Error loading taxonomies: {{ status.error }}
  </div>
  <div class="table-responsive-sm">
    <table class="table table-striped">
      <thead>
        <tr>
          <th scope="col">namespace</th>
          <!-- <th scope="col">description</th> -->
          <th scope="col">version</th>
          <th scope="col">enabled</th>
          <th scope="col">exclusive</th>
          <th scope="col">required</th>
          <th scope="col">highlighted</th>
          <th scope="col">active tags</th>
          <th scope="col" width="20%" class="text-end">actions</th>
        </tr>
      </thead>
      <tbody>
        <tr :key="taxonomy.uuid" v-for="taxonomy in taxonomies.items">
          <td>
            <RouterLink :to="`/taxonomies/${taxonomy.uuid}`">{{
              taxonomy.namespace
            }}</RouterLink>
          </td>
          <td>{{ taxonomy.version }}</td>
          <td>
            <div class="flex-wrap btn-group me-2">
              <button
                type="button"
                class="btn"
                @click="toggle('enabled', taxonomy)"
                :class="{
                  'btn-outline-success': taxonomy.enabled,
                  'btn-outline-danger': !taxonomy.enabled,
                }"
                data-toggle="tooltip"
                data-placement="top"
                title="Toggle taxonomy"
              >
                <font-awesome-icon
                  v-if="taxonomy.enabled"
                  icon="fa-solid fa-check"
                />
                <font-awesome-icon
                  v-if="!taxonomy.enabled"
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
                @click="toggle('exclusive', taxonomy)"
                :class="{
                  'btn-outline-success': taxonomy.exclusive,
                  'btn-outline-danger': !taxonomy.exclusive,
                }"
                data-toggle="tooltip"
                data-placement="top"
                title="Toggle taxonomy"
              >
                <font-awesome-icon
                  v-if="taxonomy.exclusive"
                  icon="fa-solid fa-check"
                />
                <font-awesome-icon
                  v-if="!taxonomy.exclusive"
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
                @click="toggle('required', taxonomy)"
                :class="{
                  'btn-outline-success': taxonomy.required,
                  'btn-outline-danger': !taxonomy.required,
                }"
                data-toggle="tooltip"
                data-placement="top"
                title="Toggle taxonomy"
              >
                <font-awesome-icon
                  v-if="taxonomy.required"
                  icon="fa-solid fa-check"
                />
                <font-awesome-icon
                  v-if="!taxonomy.required"
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
                @click="toggle('highlighted', taxonomy)"
                :class="{
                  'btn-outline-success': taxonomy.highlighted,
                  'btn-outline-danger': !taxonomy.highlighted,
                }"
                data-toggle="tooltip"
                data-placement="top"
                title="Toggle taxonomy"
              >
                <font-awesome-icon
                  v-if="taxonomy.highlighted"
                  icon="fa-solid fa-check"
                />
                <font-awesome-icon
                  v-if="!taxonomy.highlighted"
                  icon="fa-solid fa-xmark"
                />
              </button>
            </div>
          </td>
          <td>-</td>
          <td>
            <TaxonomyActions
              :taxonomy="taxonomy"
              @taxonomy-deleted="handleTaxonomiesUpdated"
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
