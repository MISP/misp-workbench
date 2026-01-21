<script setup>
import Badge from "@/components/misc/Badge.vue";
import CopyToClipboard from "@/components/misc/CopyToClipboard.vue";
import UUID from "@/components/misc/UUID.vue";
defineProps(["galaxy", "status"]);

function handleGalaxyDeleted() {
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
    <div class="galaxy-title card-header border-bottom">
      <div class="row">
        <div class="col-10">
          <h3>{{ galaxy.name }}</h3>
        </div>
        <div class="col-2 text-end">
          <div
            class="flex-wrap"
            :class="{
              'btn-group-vertical': $isMobile,
              'btn-group': !$isMobile,
            }"
            aria-label="Galaxy Actions"
          >
            <button
              type="button"
              class="btn btn-outline-danger"
              data-bs-toggle="modal"
              :data-bs-target="'#deleteGalaxyModal-' + galaxy.id"
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
                    <th>uuid</th>
                    <td>
                      <UUID :uuid="galaxy.uuid" :copy="true" />
                    </td>
                  </tr>
                  <tr>
                    <th>description</th>
                    <td>{{ galaxy.description }}</td>
                  </tr>
                  <tr>
                    <th>version</th>
                    <td>{{ galaxy.version }}</td>
                  </tr>
                  <tr>
                    <th>enabled</th>
                    <td>{{ galaxy.enabled }}</td>
                  </tr>
                  <tr>
                    <th>exclusive</th>
                    <td>{{ galaxy.local_only }}</td>
                  </tr>
                  <tr>
                    <th>required</th>
                    <td>{{ galaxy.default }}</td>
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
                        <th scope="col">uuid</th>
                        <th scope="col">value</th>
                        <th scope="col">connector_tag</th>
                        <th scope="col">deleted</th>
                        <th scope="col">published</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr
                        v-for="cluster in galaxy.clusters"
                        :key="cluster.uuid"
                      >
                        <td>
                          <UUID :uuid="cluster.uuid" :copy="true" />
                        </td>
                        <td>{{ cluster.value }}</td>
                        <td>
                          <Badge :value="cluster.tag_name" />
                          <CopyToClipboard :value="cluster.tag_name" />
                        </td>
                        <td>{{ cluster.deleted }}</td>
                        <td>{{ cluster.published }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    <DeleteGalaxyModal
      @galaxy-deleted="handleGalaxyDeleted"
      :galaxy_id="galaxy.id"
    />
  </div>
</template>
