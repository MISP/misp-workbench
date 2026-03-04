<script setup>
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
      <div class="attribute-title card-header border-bottom">
        <div class="row align-items-center">
          <div class="col-md-8 col-sm-12">
            <h6 class="mb-0 text-truncate">
              <RouterLink
                :to="`/events/${object.event_uuid}`"
                class="text-decoration-none text-primary"
              >
                Event #{{ object.event_uuid }}
              </RouterLink>
              <span class="text-muted"> / </span>
              <span class="text-secondary"
                >Object
                <span class="badge badge-pill bg-secondary">
                  {{ object.name }}</span
                >
                #{{ object.uuid }}</span
              >
            </h6>
          </div>
          <div
            class="col-md-4 col-sm-12 text-md-end text-sm-start mt-sm-2 mt-md-0"
          >
            <ObjectActions
              :object="object"
              @object-deleted="handleObjectDeleted"
            />
          </div>
        </div>
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
