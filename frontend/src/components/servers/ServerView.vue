<script setup>
import DeleteServerModal from "@/components/servers/DeleteServerModal.vue";

import { router } from "@/router";

defineProps(["server"]);

function handleServerDeleted(event) {
  router.push(`/servers`);
}
</script>

<template>
  <div class="card">
    <div class="card-header border-bottom">
      <div class="row">
        <div class="col-10">
          <h3>{{ server.name }}</h3>
        </div>
        <div class="col-2 text-end">
          <div
            class="flex-wrap"
            :class="{
              'btn-group-vertical': $isMobile,
              'btn-group': !$isMobile,
            }"
            aria-label="Server Actions"
          >
            <button
              type="button"
              class="btn btn-outline-danger"
              data-bs-toggle="modal"
              :data-bs-target="'#deleteServerModal-' + server.id"
            >
              <font-awesome-icon icon="fa-solid fa-trash" />
            </button>
            <RouterLink
              :to="`/servers/update/${server.id}`"
              tag="button"
              class="btn btn-outline-primary"
            >
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
              <td>{{ server.id }}</td>
            </tr>
            <tr>
              <th style="width: 30%">url</th>
              <td>{{ server.url }}</td>
            </tr>
            <tr>
              <th style="width: 30%">org_id</th>
              <td>{{ server.org_id }}</td>
            </tr>
            <tr>
              <th style="width: 30%">push</th>
              <td>{{ server.push }}</td>
            </tr>
            <tr>
              <th style="width: 30%">pull</th>
              <td>{{ server.pull }}</td>
            </tr>
            <tr>
              <th style="width: 30%">push_sightings</th>
              <td>{{ server.push_sightings }}</td>
            </tr>
            <tr>
              <th style="width: 30%">push_galaxy_clusters</th>
              <td>{{ server.push_galaxy_clusters }}</td>
            </tr>
            <tr>
              <th style="width: 30%">pull_galaxy_clusters</th>
              <td>{{ server.pull_galaxy_clusters }}</td>
            </tr>
            <tr>
              <th style="width: 30%">last_pulled_id</th>
              <td>{{ server.last_pulled_id }}</td>
            </tr>
            <tr>
              <th style="width: 30%">last_pushed_id</th>
              <td>{{ server.last_pushed_id }}</td>
            </tr>
            <tr>
              <th style="width: 30%">organisation</th>
              <td>{{ server.organisation }}</td>
            </tr>
            <tr>
              <th style="width: 30%">remote_org_id</th>
              <td>{{ server.remote_org_id }}</td>
            </tr>
            <tr>
              <th style="width: 30%">publish_without_email</th>
              <td>{{ server.publish_without_email }}</td>
            </tr>
            <tr>
              <th style="width: 30%">unpublish_event</th>
              <td>{{ server.unpublish_event }}</td>
            </tr>
            <tr>
              <th style="width: 30%">self_signed</th>
              <td>{{ server.self_signed }}</td>
            </tr>
            <tr>
              <th style="width: 30%">pull_rules</th>
              <td>{{ server.pull_rules }}</td>
            </tr>
            <tr>
              <th style="width: 30%">push_rules</th>
              <td>{{ server.push_rules }}</td>
            </tr>
            <tr>
              <th style="width: 30%">cert_file</th>
              <td>{{ server.cert_file }}</td>
            </tr>
            <tr>
              <th style="width: 30%">client_cert_file</th>
              <td>{{ server.client_cert_file }}</td>
            </tr>
            <tr>
              <th style="width: 30%">internal</th>
              <td>{{ server.internal }}</td>
            </tr>
            <tr>
              <th style="width: 30%">skip_proxy</th>
              <td>{{ server.skip_proxy }}</td>
            </tr>
            <tr>
              <th style="width: 30%">caching_enabled</th>
              <td>{{ server.caching_enabled }}</td>
            </tr>
            <tr>
              <th style="width: 30%">priority</th>
              <td>{{ server.priority }}</td>
            </tr>
          </tbody>
        </table>
        <DeleteServerModal
          @server-deleted="handleServerDeleted"
          :server_id="server.id"
        />
      </div>
    </div>
  </div>
</template>
