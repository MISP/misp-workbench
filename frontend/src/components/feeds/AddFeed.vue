<script setup>
import { ref, computed, watch, reactive } from "vue";
import { router } from "@/router";
import { useFeedsStore, useToastsStore, useTasksStore } from "@/stores";

import FeedTypeSelector from "@/components/feeds/FeedTypeSelector.vue";
import FeedBaseForm from "@/components/feeds/FeedBaseForm.vue";
import AddFeedMISP from "@/components/feeds/misp/AddFeedMISP.vue";
import AddFeedCsv from "@/components/feeds/csv/AddFeedCsv.vue";
import TestCSVFeedModal from "@/components/feeds/csv/TestCSVFeedModal.vue";
import TestMISPFeedConnectionModal from "@/components/feeds/misp/TestMISPFeedConnectionModal.vue";
import AddFeedJson from "@/components/feeds/json/AddFeedJson.vue";

const feedsStore = useFeedsStore();
const toastsStore = useToastsStore();
const tasksStore = useTasksStore();

const feedType = ref("misp");
const apiError = ref(null);

const config = ref({
  name: "",
  url: "",
  input_source: "network",
  enabled: true,
  schedule: "86400",
  provider: "",
  distribution: 1,
  fetch_on_create: true,
  rules: {},
  settings: {},
});

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
const testMISPFeedResultOpen = ref(false);
const testMISPFeedResult = reactive({
  success: false,
  message: "",
  total_events: 0,
});
const testCSVFeedResultOpen = ref(false);
const testCSVFeedResult = reactive({});

/**
 * Reset type-specific config when switching types
 * (prevents leaking CSV mapping into JSON, etc.)
 */
watch(feedType, () => {
  config.value.rules = {};
  config.value.settings = {};
});

const canSubmit = computed(() => {
  return config.value.name && config.value.url;
});

function submit() {
  const feed = {
    ...getFeedFromConfig(),
    rules: config.value.rules,
    settings: config.value.settings,
  };

  return feedsStore
    .create(feed)
    .then((response) => {
      // Create scheduled task if schedule is defined
      if (config.value.schedule && config.value.schedule !== "disabled") {
        const intervalSeconds = parseInt(config.value.schedule);

        const taskData = {
          task_name: "app.worker.tasks.fetch_feed",
          params: {
            kwargs: {
              feed_id: response.id,
            },
          },
          schedule: {
            type: "interval",
            every: intervalSeconds,
          },
          enabled: response.enabled,
        };

        tasksStore.create_scheduled_task(taskData).catch((error) => {
          console.error("Failed to create scheduled task:", error);
          // Continue with feed creation even if task creation fails
        });
      }

      toastsStore.push(
        `Feed "${response.name}" created successfully!`,
        "success",
      );
      router.push(`/feeds`);
    })
    .catch((error) => (apiError.value = error?.message || String(error)));
}

function getFeedFromConfig() {
  return {
    name: config.value.name,
    url: config.value.url,
    provider: config.value.provider,
    source_format: feedType.value,
    enabled: config.value.enabled,
    distribution: parseInt(config.value.distribution),
    input_source: config.value.input_source,
  };
}

function cancel() {
  router.push(`/feeds`);
}

function test() {
  const feed = {
    type: feedType.value,
    config: config.value,
  };

  if (feed.type === "misp") {
    return testMISPFeed();
  }

  if (feed.type === "csv") {
    testCSVFeed();
  }
}

function testMISPFeed() {
  const mispFeed = {
    ...getFeedFromConfig(),
    rules: config.value.rules,
  };

  return feedsStore
    .testMISPFeedConnection(mispFeed)
    .then((response) => {
      if (response.result === "success") {
        testMISPFeedResult.success = true;
        testMISPFeedResult.message = `Connection successful!`;
        testMISPFeedResult.total_events = response.total_events;
        testMISPFeedResult.total_filtered_events =
          response.total_filtered_events;
      } else {
        testMISPFeedResult.success = false;
        testMISPFeedResult.message = `Connection failed: ${response.message}`;
      }
      testMISPFeedResultOpen.value = true;
    })
    .catch((error) => {
      testMISPFeedResult.success = false;
      testMISPFeedResult.message = error?.message || String(error);
      testMISPFeedResultOpen.value = true;
    });
}

function testCSVFeed() {
  const csvFeed = {
    ...getFeedFromConfig(),
    settings: config.value.settings,
  };

  return feedsStore
    .previewCsvFeed(csvFeed)
    .then((response) => {
      testCSVFeedResult.value = response;
      testCSVFeedResultOpen.value = true;
    })
    .catch((error) => {
      testCSVFeedResult.success = false;
      testCSVFeedResult.message = error?.message || String(error);
      testCSVFeedResultOpen.value = true;
    });
}

function closeMISPFeedTestResult() {
  testMISPFeedResultOpen.value = false;
}
function closeCSVFeedTestResult() {
  testCSVFeedResultOpen.value = false;
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
              <FeedBaseForm v-model="config" />
            </div>
          </div>
        </div>

        <div class="mb-4">
          <component :is="typeComponent" v-model="config" />
        </div>
        <div v-if="apiError" class="w-100 alert alert-danger mt-3 mb-3">
          {{ apiError }}
        </div>
        <div class="d-flex justify-content-end gap-2">
          <button class="btn btn-outline-secondary" @click="cancel">
            Cancel
          </button>
          <button class="btn btn-success" :disabled="!canSubmit" @click="test">
            Preview
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
  <TestMISPFeedConnectionModal
    v-if="testMISPFeedResultOpen"
    :testResult="testMISPFeedResult"
    @closeModal="closeMISPFeedTestResult"
  />
  <TestCSVFeedModal
    v-if="testCSVFeedResultOpen"
    :config="config"
    :testResult="testCSVFeedResult.value"
    @closeModal="closeCSVFeedTestResult"
  />
</template>
