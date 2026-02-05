<script setup>
import { ref, computed, watch, reactive } from "vue";
import { router } from "@/router";
import { useFeedsStore, useToastsStore } from "@/stores";

import FeedTypeSelector from "@/components/feeds/FeedTypeSelector.vue";
import FeedBaseForm from "@/components/feeds/FeedBaseForm.vue";
import AddFeedMISP from "@/components/feeds/AddFeedMISP.vue";
import AddFeedCsv from "@/components/feeds/AddFeedCsv.vue";
import AddFeedJson from "@/components/feeds/AddFeedJson.vue";

const feedsStore = useFeedsStore();
const toastsStore = useToastsStore();

const feedType = ref("misp");
const apiError = ref(null);

const baseConfig = ref({
  name: "",
  url: "",
  input_source: "network",
  enabled: true,
  schedule: "daily",
  provider: "",
  distribution: 0,
  fetch_on_create: true,
});

const typeConfig = ref(null);

const typeComponent = computed(() => {
  switch (feedType.value) {
    case "csv":
      return AddFeedCsv;
    case "json":
      return AddFeedJson;
    case "misp":
    default:
      return AddFeedMISP;
  }
});

// test modal state
const testResultOpen = ref(false);
const testResult = reactive({ success: false, message: "", total_events: 0 });

/**
 * Reset type-specific config when switching types
 * (prevents leaking CSV mapping into JSON, etc.)
 */
watch(feedType, () => {
  typeConfig.value = {};
});

const canSubmit = computed(() => {
  return baseConfig.value.name && baseConfig.value.url;
});

function submit() {
  const feed = {
    type: feedType.value,
    config: {
      ...baseConfig.value,
      ...typeConfig.value,
    },
  };

  if (feed.type === "misp") {
    const mispFeed = getMispFeedFromConfig();

    return feedsStore
      .create(mispFeed)
      .then((response) => {
        console.log("Feed created:", response);
        toastsStore.push(
          `Feed "${response.name}" created successfully!`,
          "success",
        );
        router.push(`/feeds`);
      })
      .catch((error) => (apiError.value = error?.message || String(error)));
  }
}

function getMispFeedFromConfig() {
  return {
    name: baseConfig.value.name,
    url: baseConfig.value.url,
    provider: baseConfig.value.provider,
    source_format: feedType.value,
    enabled: baseConfig.value.enabled,
    distribution: baseConfig.value.distribution,
    input_source: baseConfig.value.input_source,
    rules: typeConfig.value.rules,
  };
}

function cancel() {
  router.push(`/feeds`);
}

function test() {
  const feed = {
    type: feedType.value,
    config: {
      ...baseConfig.value,
      ...typeConfig.value,
    },
  };

  if (feed.type === "misp") {
    const mispFeed = getMispFeedFromConfig();

    return feedsStore
      .testConnection(mispFeed)
      .then((response) => {
        if (response.result == "success") {
          testResult.success = true;
          testResult.message = `Connection successful!`;
          testResult.total_events = response.total_events;
          testResult.total_filtered_events = response.total_filtered_events;
        } else {
          testResult.success = false;
          testResult.message = `Connection failed: ${response.message}`;
        }
        testResultOpen.value = true;
      })
      .catch((error) => {
        testResult.success = false;
        testResult.message = error?.message || String(error);
        testResultOpen.value = true;
      });
  }
}

function closeTestResult() {
  testResultOpen.value = false;
}
</script>

<style scoped>
.add-feed-card {
  width: fit-content;
}

/* Test modal styles */
.test-modal-backdrop {
  position: fixed;
  left: 0;
  top: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
}

.test-modal .card {
  width: 520px;
  max-width: calc(100% - 2rem);
}
</style>

<template>
  <div class="add-feed-card card mx-auto">
    <div class="card-header border-bottom">
      <div class="row">
        <div>
          <h3>Add Feed</h3>
        </div>
      </div>
    </div>
    <div class="card-body d-flex flex-column">
      <div class="container-lg">
        <div class="mb-4">
          <p class="text-muted mb-0">
            Configure an external feed and how its data is ingested.
          </p>
        </div>

        <div class="mb-4">
          <FeedTypeSelector v-model="feedType" />
        </div>

        <div class="mb-4">
          <div class="card">
            <div class="card-header">
              <h5 class="mb-0">Feed Settings</h5>
            </div>
            <div class="card-body">
              <FeedBaseForm v-model="baseConfig" />
            </div>
          </div>
        </div>

        <div class="mb-4">
          <component :is="typeComponent" v-model="typeConfig" />
        </div>
        <div v-if="apiError" class="w-100 alert alert-danger mt-3 mb-3">
          {{ apiError }}
        </div>
        <div class="d-flex justify-content-end gap-2">
          <button class="btn btn-outline-secondary" @click="cancel">
            Cancel
          </button>
          <button class="btn btn-success" :disabled="!canSubmit" @click="test">
            Test
          </button>
          <button
            class="btn btn-primary"
            :disabled="!canSubmit"
            @click="submit"
          >
            Add Feed
          </button>
        </div>
      </div>
    </div>
  </div>
  <div v-if="testResultOpen" class="test-modal-backdrop">
    <div class="test-modal">
      <div class="card">
        <div
          class="card-header d-flex justify-content-between align-items-center"
        >
          <div>
            <strong>Connection Test</strong>
          </div>
        </div>
        <div class="card-body">
          <div v-if="testResult.success" class="alert alert-success">
            {{ testResult.message }}
          </div>
          <div v-else class="alert alert-danger">
            {{ testResult.message }}
          </div>
          <div v-if="testResult.total_events">
            <p class="mb-0">
              <strong>Total feed events:</strong> {{ testResult.total_events }}
            </p>
          </div>
          <div v-if="testResult.total_filtered_events">
            <p class="mb-0">
              <strong>Total events to fetch:</strong>
              {{ testResult.total_filtered_events }}
            </p>
          </div>
        </div>
        <div class="card-footer text-end">
          <button class="btn btn-secondary" @click="closeTestResult">
            Close
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
