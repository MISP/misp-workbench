<script setup>
import Sparkline from "@/components/charts/Sparkline.vue";
import DistributionLevel from "@/components/enums/DistributionLevel.vue";
import ObjectAttributesList from "@/components/objects/ObjectAttributesList.vue";
import ObjectActions from "@/components/objects/ObjectActions.vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faCubesStacked } from "@fortawesome/free-solid-svg-icons";

defineProps(["object", "status"]);

function handleObjectDeleted() {
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
    <span v-show="status.loading">
      <span
        class="spinner-border spinner-border-sm"
        role="status"
        aria-hidden="true"
      ></span>
    </span>
    <div v-if="!status.loading">
      <div class="card-header">
        <span class="h4"> {{ object.name }} #{{ object.id }} </span>
        <ObjectActions :object="object" @object-deleted="handleObjectDeleted" />
      </div>
      <div class="row m-1">
        <div class="col-sm-6 mt-2">
          <div class="card">
            <div class="card-body d-flex flex-column">
              <div class="table-responsive-sm">
                <table class="table table-striped">
                  <tbody>
                    <tr>
                      <th>id</th>
                      <td>{{ object.id }}</td>
                    </tr>
                    <tr>
                      <th>uuid</th>
                      <td>
                        {{ object.uuid }}
                        <font-awesome-icon
                          class="text-primary"
                          icon="fa-solid fa-copy"
                        />
                      </td>
                    </tr>
                    <tr>
                      <th>category</th>
                      <td>{{ object.meta_category }}</td>
                    </tr>
                    <tr>
                      <th>template</th>
                      <td>{{ object.name }}</td>
                    </tr>
                    <tr>
                      <th>version</th>
                      <td>{{ object.version }}</td>
                    </tr>
                    <tr>
                      <th>comment</th>
                      <td>{{ object.comment }}</td>
                    </tr>
                    <tr>
                      <th>timestamp</th>
                      <td>{{ object.timestamp }}</td>
                    </tr>
                    <tr>
                      <th>distribution</th>
                      <td>
                        <DistributionLevel
                          :distribution_level_id="object.distribution"
                        />
                      </td>
                    </tr>
                    <tr>
                      <th>first seen</th>
                      <td>{{ object.first_seen }}</td>
                    </tr>
                    <tr>
                      <th>last seen</th>
                      <td>{{ object.last_seen }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
        <div class="col-xs-12 col-sm-12 col-md-12 col-lg-6 col-xl-3">
          <div class="mt-2 card">
            <div class="card-body">
              <div class="d-flex justify-content-between align-items-center">
                <div>
                  <p class="mb-0 text-muted">activity</p>
                  <Sparkline :data="[2, 3, 5, 7, 18, 8, 6, 15, 23, 20, 21]" />
                </div>
              </div>
            </div>
            <div class="card-footer text-muted">
              <p class="card-text fst-italic fw-light">
                <small class="text-muted"
                  >last day/week/<span class="fw-bold text-decoration-underline"
                    >month</span
                  ></small
                >
              </p>
            </div>
          </div>
          <div class="mt-2 card">
            <div class="card-body">
              <div class="d-flex justify-content-between align-items-center">
                <div>
                  <p class="mb-0 text-muted">sightings</p>
                  <h2>423</h2>
                </div>
                <span
                  class="badge badge-pill badge-cyan badge-red bg-danger fs-5"
                >
                  <font-awesome-icon icon="fa-solid fa-up-long" />
                  <span class="font-weight-semibold ml-1">16.71%</span>
                </span>
              </div>
            </div>
            <div class="card-footer text-muted">
              <p class="card-text fst-italic fw-light">
                <small class="text-muted"
                  >last day/week/<span class="fw-bold text-decoration-underline"
                    >month</span
                  ></small
                >
              </p>
            </div>
          </div>
        </div>
      </div>
      <div class="card m-3">
        <div class="card-header">
          <FontAwesomeIcon :icon="faCubesStacked" /> attributes
        </div>
        <div class="card-body d-flex flex-column">
          <ObjectAttributesList
            :attributes="object.attributes"
            :object_id="object.id"
          />
        </div>
      </div>
    </div>
  </div>
</template>
