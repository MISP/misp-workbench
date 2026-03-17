<script setup>
import { ref, reactive } from "vue";
import { storeToRefs } from "pinia";
import { useFeedsStore, useToastsStore } from "@/stores";
import { router } from "@/router";
import FeedBaseForm from "@/components/feeds/FeedBaseForm.vue";
import AddFeedMISP from "@/components/feeds/misp/AddFeedMISP.vue";
import TestMISPFeedConnectionModal from "@/components/feeds/misp/TestMISPFeedConnectionModal.vue";

const feedsStore = useFeedsStore();
const toastsStore = useToastsStore();
const { feed, status } = storeToRefs(feedsStore);

const apiError = ref(null);

const config = ref({
  name: feed.value.name,
  url: feed.value.url,
  provider: feed.value.provider,
  distribution: feed.value.distribution,
  enabled: feed.value.enabled,
  fixed_event: feed.value.fixed_event,
  input_source: feed.value.input_source,
  headers: feed.value.headers ?? {},
  rules: feed.value.rules ?? {},
});

// test modal state
const testResultOpen = ref(false);
const testResult = reactive({
  success: false,
  message: "",
  total_events: 0,
});

function submit() {
  const payload = {
    id: feed.value.id,
    name: config.value.name,
    url: config.value.url,
    provider: config.value.provider,
    source_format: "misp",
    distribution: parseInt(config.value.distribution),
    enabled: config.value.enabled,
    fixed_event: config.value.fixed_event,
    input_source: config.value.input_source,
    headers: config.value.headers ?? {},
    rules: config.value.rules ?? {},
  };

  return feedsStore
    .update(payload)
    .then(() => {
      toastsStore.push(
        `Feed "${payload.name}" updated successfully!`,
        "success",
      );
      router.push(`/feeds/${feed.value.id}`);
    })
    .catch((error) => (apiError.value = error?.message || String(error)));
}

function cancel() {
  router.push(`/feeds/${feed.value.id}`);
}

function test() {
  const payload = {
    name: config.value.name,
    url: config.value.url,
    provider: config.value.provider,
    source_format: "misp",
    distribution: parseInt(config.value.distribution),
    enabled: config.value.enabled,
    fixed_event: config.value.fixed_event,
    input_source: config.value.input_source,
    headers: config.value.headers ?? {},
    rules: config.value.rules ?? {},
  };

  return feedsStore
    .testMISPFeedConnection(payload)
    .then((response) => {
      if (response.result === "success") {
        testResult.success = true;
        testResult.message = "Connection successful!";
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

function closeTestResult() {
  testResultOpen.value = false;
}
</script>

<template>
  <div class="card">
    <div class="card-header border-bottom">
      <h3>Update MISP Feed</h3>
    </div>
    <div class="card-body d-flex flex-column">
      <div class="container-lg">
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
          <AddFeedMISP v-model="config" />
        </div>

        <div v-if="apiError" class="w-100 alert alert-danger mt-3 mb-3">
          {{ apiError }}
        </div>

        <div class="d-flex justify-content-end gap-2">
          <button class="btn btn-outline-secondary" @click="cancel">
            Cancel
          </button>
          <button class="btn btn-success" @click="test">Test Connection</button>
          <button
            class="btn btn-primary"
            :class="{ disabled: status.updating }"
            @click="submit"
          >
            <span v-if="status.updating">
              <span
                class="spinner-border spinner-border-sm"
                role="status"
                aria-hidden="true"
              ></span>
            </span>
            <span v-else>Save</span>
          </button>
        </div>
      </div>
    </div>
  </div>
  <TestMISPFeedConnectionModal
    v-if="testResultOpen"
    :testResult="testResult"
    @closeModal="closeTestResult"
  />
</template>
