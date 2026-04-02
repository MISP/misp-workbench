<script setup>
import FeedActions from "@/components/feeds/FeedActions.vue";
import ViewFeedMISP from "@/components/feeds/misp/ViewFeedMISP.vue";
import { DISTRIBUTION_LEVEL } from "@/helpers/constants";
import { computed } from "vue";
import { router } from "@/router";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faLink } from "@fortawesome/free-solid-svg-icons";

const props = defineProps(["feed"]);

function handleFeedDeleted() {
  router.push(`/feeds`);
}

const distributionLabel = computed(() => {
  const entry = Object.entries(DISTRIBUTION_LEVEL).find(
    ([, v]) => v === props.feed.distribution,
  );
  return entry ? entry[0].replace(/_/g, " ") : props.feed.distribution;
});

const sourceFormatLabel = computed(() => {
  const map = {
    misp: "MISP Feed",
    csv: "CSV",
    freetext: "Freetext",
    json: "JSON",
  };
  return map[props.feed.source_format] ?? props.feed.source_format;
});
</script>

<template>
  <div class="card">
    <div class="card-header border-bottom">
      <div class="row align-items-center">
        <div class="col">
          <h3 class="mb-0">{{ feed.name }}</h3>
        </div>
        <div class="col-auto">
          <FeedActions
            :feed="feed"
            :default_actions="{ read: false }"
            @feed-deleted="handleFeedDeleted"
          />
        </div>
      </div>
    </div>
    <div class="card-body">
      <div class="container-lg">
        <!-- Feed Settings -->
        <div class="mb-4">
          <div class="card">
            <div class="card-header">
              <h5 class="mb-0">Feed Settings</h5>
            </div>
            <div class="card-body">
              <div class="row g-3">
                <div class="col-md-6">
                  <label class="form-label text-muted small">Name</label>
                  <div>{{ feed.name }}</div>
                </div>
                <div class="col-md-6 d-flex align-items-end">
                  <span
                    class="badge"
                    :class="feed.enabled ? 'bg-success' : 'bg-secondary'"
                  >
                    {{ feed.enabled ? "Enabled" : "Disabled" }}
                  </span>
                </div>
                <div class="col-md-6">
                  <label class="form-label text-muted small">Provider</label>
                  <div>{{ feed.provider }}</div>
                </div>
                <div class="col-md-6">
                  <label class="form-label text-muted small"
                    >Distribution</label
                  >
                  <div>{{ distributionLabel }}</div>
                </div>
                <div class="col-md-6">
                  <label class="form-label text-muted small"
                    >Source Format</label
                  >
                  <div>
                    <span class="badge bg-primary">{{
                      sourceFormatLabel
                    }}</span>
                  </div>
                </div>
                <div class="col-md-6">
                  <label class="form-label text-muted small"
                    >Input Source</label
                  >
                  <div>{{ feed.input_source }}</div>
                </div>
                <div class="col-10">
                  <label class="form-label text-muted small">URI</label>
                  <div class="input-group">
                    <span class="input-group-text">
                      <FontAwesomeIcon :icon="faLink" />
                    </span>
                    <span
                      class="form-control text-break"
                      style="cursor: default"
                      >{{ feed.url }}</span
                    >
                  </div>
                </div>
                <div class="col-md-12">
                  <label class="form-label text-muted small">Fixed Event</label>
                  <div>
                    <span
                      class="badge"
                      :class="feed.fixed_event ? 'bg-primary' : 'bg-secondary'"
                    >
                      {{ feed.fixed_event ? "Yes" : "No" }}
                    </span>
                    <span class="text-muted small ms-2">
                      {{
                        feed.fixed_event
                          ? "All attributes go into a single event"
                          : "A new event is created per fetch"
                      }}
                    </span>
                  </div>
                </div>
                <div
                  v-if="feed.headers && Object.keys(feed.headers).length"
                  class="col-md-12"
                >
                  <label class="form-label text-muted small"
                    >Authentication</label
                  >
                  <div>
                    <span class="badge bg-info text-dark">Auth Header</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Rules (MISP feeds) -->
        <div v-if="feed.source_format === 'misp'" class="mb-4">
          <ViewFeedMISP :feed="feed" />
        </div>

        <!-- Settings (non-MISP feeds) -->
        <div
          v-if="
            feed.source_format !== 'misp' &&
            feed.settings &&
            Object.keys(feed.settings).length
          "
          class="mb-4"
        >
          <div class="card">
            <div class="card-header">
              <h5 class="mb-0">Feed Settings</h5>
            </div>
            <div class="card-body">
              <pre class="mb-0 small">{{
                JSON.stringify(feed.settings, null, 2)
              }}</pre>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
