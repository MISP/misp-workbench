<script setup>
import Badge from "@/components/misc/Badge.vue";
const props = defineProps(["taxonomy", "status"]);

function handleTaxonomyDeleted(event) {
  router.go(-1);
}
</script>

<style>
.single-stat-card .card-body {
  font-size: x-large;
  text-align: center;
  padding: 0;
}

div.row h3 {
  margin-bottom: 0;
}

.single-stat-card .card-body p {
  margin-bottom: 0;
}
</style>
<template>
  <div class="card">
    <div class="taxonomy-title card-header border-bottom">
      <div class="row">
        <div class="col-10">
          <h3>Taxonomy #{{ taxonomy.id }}</h3>
        </div>
        <div class="col-2 text-end">
          <div
            class="flex-wrap"
            :class="{
              'btn-group-vertical': $isMobile,
              'btn-group': !$isMobile,
            }"
            aria-label="Taxonomy Actions"
          >
            <button
              type="button"
              class="btn btn-outline-danger"
              data-bs-toggle="modal"
              :data-bs-target="'#deleteTaxonomyModal-' + taxonomy.id"
            >
              <font-awesome-icon icon="fa-solid fa-trash" />
            </button>
          </div>
        </div>
      </div>
    </div>
    <div class="row m-1">
      <div class="mt-2">
        <div class="card">
          <div class="card-body d-flex flex-column">
            <div class="table-responsive-sm">
              <table class="table table-striped">
                <tbody>
                  <tr>
                    <th>id</th>
                    <td>{{ taxonomy.id }}</td>
                  </tr>
                  <tr>
                    <th>description</th>
                    <td>{{ taxonomy.description }}</td>
                  </tr>
                  <tr>
                    <th>version</th>
                    <td>{{ taxonomy.version }}</td>
                  </tr>
                  <tr>
                    <th>enabled</th>
                    <td>{{ taxonomy.enabled }}</td>
                  </tr>
                  <tr>
                    <th>exclusive</th>
                    <td>{{ taxonomy.exclusive }}</td>
                  </tr>
                  <tr>
                    <th>required</th>
                    <td>{{ taxonomy.required }}</td>
                  </tr>
                  <tr>
                    <th>highlighted</th>
                    <td>{{ taxonomy.highlighted }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
        <div class="row">
          <div class="mt-2">
            <div class="card">
              <div class="card-body d-flex flex-column">
                <div class="table-responsive-sm">
                  <table class="table table-striped">
                    <thead>
                      <tr>
                        <th scope="col">id</th>
                        <th scope="col">tag</th>
                        <th scope="col">expanded</th>
                      </tr>
                    </thead>
                    <tbody>
                      <template
                        v-for="predicate in taxonomy.predicates"
                        :key="predicate.id"
                      >
                        <tr
                          v-if="predicate.entries.length"
                          v-for="entry in predicate.entries"
                          :key="entry.id"
                        >
                          <td>{{ entry.id }}</td>
                          <td>
                            <Badge
                              :value="entry.value"
                              :namespace="taxonomy.namespace"
                              :colour="entry.colour"
                            />
                          </td>
                          <td>{{ entry.expanded }}</td>
                        </tr>
                        <tr v-if="!predicate.entries.length">
                          <td>{{ predicate.id }}</td>
                          <td>
                            <Badge
                              :value="predicate.value"
                              :namespace="taxonomy.namespace"
                              :colour="predicate.colour"
                            />
                          </td>
                          <td>{{ predicate.expanded }}</td>
                        </tr>
                      </template>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    <DeleteTaxonomyModal
      @taxonomy-deleted="handleTaxonomyDeleted"
      :taxonomy_id="taxonomy.id"
    />
  </div>
</template>
