<script setup>
import Spinner from "@/components/misc/Spinner.vue";
import { storeToRefs } from "pinia";
import { useCorrelationsStore, useToastsStore } from "@/stores";
const correlationsStore = useCorrelationsStore();
const toastsStore = useToastsStore();
const { stats, status } = storeToRefs(correlationsStore);

correlationsStore.getStats();

async function rerunCorrelations() {
  correlationsStore.run().then((response) => {
    toastsStore.push(
      "Correlations re-run enqueued. Task ID: " + response.task_id,
    );
  });
}
</script>

<template>
  <div class="container mt-4">
    <Spinner v-if="status.loading" />
    <div class="card shadow">
      <div
        class="card-header d-flex align-items-center justify-content-between"
      >
        <h5 class="mb-0">Correlations</h5>
      </div>
      <div class="card-body">
        <div class="card shadow">
          <div
            class="card-header d-flex align-items-center justify-content-between"
          >
            <h6 class="mb-0">Top Attribute Correlations</h6>
          </div>
          <div class="card-body">
            <div class="table-responsive-sm">
              <table class="table table-striped">
                <thead>
                  <th>count</th>
                  <th>type</th>
                  <th>value</th>
                  <th>event_uuid</th>
                </thead>
                <tbody>
                  <tr
                    v-for="attribute in stats.top_correlated_attributes"
                    :key="attribute.key"
                    class="mb-2"
                  >
                    <td>{{ attribute.doc_count }}</td>
                    <td>
                      <span class="badge bg-primary me-2">{{
                        attribute.top_attribute_info.hits.hits[0]._source
                          .target_attribute_type
                      }}</span>
                    </td>
                    <td>
                      <RouterLink :to="`/attributes/${attribute.key}`">
                        {{
                          attribute.top_attribute_info.hits.hits[0]._source
                            .target_attribute_value
                        }}
                      </RouterLink>
                    </td>
                    <td>
                      <RouterLink
                        :to="`/events/${attribute.top_attribute_info.hits.hits[0]._source.target_event_uuid}`"
                      >
                        {{
                          attribute.top_attribute_info.hits.hits[0]._source
                            .target_event_uuid
                        }}
                      </RouterLink>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
          <div class="card-footer">
            <span
              >Total correlations:
              <strong> {{ stats.total_correlations }}</strong></span
            >
          </div>
        </div>
        <div class="card shadow mt-3">
          <div
            class="card-header d-flex align-items-center justify-content-between"
          >
            <h6 class="mb-0">Top Correlating Events</h6>
          </div>
          <div class="card-body">
            <div class="table-responsive-sm">
              <table class="table table-striped">
                <thead>
                  <th>count</th>
                  <th>event_uuid</th>
                </thead>
                <tbody>
                  <tr
                    v-for="(event, index) in stats.top_correlated_events"
                    :key="index"
                    class="mb-2"
                  >
                    <td>{{ event.doc_count }}</td>
                    <td>
                      <RouterLink :to="`/events/${event.key}`">
                        {{ event.key }}
                      </RouterLink>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
      <button
        class="btn btn-danger btn-sm"
        @click="rerunCorrelations"
        :disabled="status.generating"
      >
        <span v-if="!status.generating">Re-run Correlations</span>
        <span v-else>Running...</span>
      </button>
    </div>
  </div>
</template>
