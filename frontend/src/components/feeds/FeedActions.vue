<script setup>
import { authHelper } from "@/helpers";
import { ref, computed, onMounted, onBeforeUnmount } from "vue";
import { Modal } from "bootstrap";
import { storeToRefs } from "pinia";
import { useFeedsStore, useToastsStore, useAuthStore } from "@/stores";
import DeleteFeedModal from "@/components/feeds/DeleteFeedModal.vue";
import PreviewFeedModal from "@/components/feeds/misp/PreviewFeedModal.vue";

const authStore = useAuthStore();
const { scopes } = storeToRefs(authStore);

const props = defineProps({
  feed: { type: Object, required: true },
  default_actions: { type: Object, default: () => ({}) },
});
const emit = defineEmits(["feed-deleted"]);

const previewOpen = ref(false);
const previewResult = ref(null);
const previewError = ref(null);
const previewing = ref(false);

const actions = computed(() => ({
  read:
    props.default_actions.read ??
    authHelper.hasScope(scopes.value, "feeds:read"),
  update:
    props.default_actions.update ??
    authHelper.hasScope(scopes.value, "feeds:update"),
  delete:
    props.default_actions.delete ??
    authHelper.hasScope(scopes.value, "feeds:delete"),
  fetch:
    props.default_actions.fetch ??
    authHelper.hasScope(scopes.value, "feeds:fetch"),
}));

const deleteFeedModal = ref(null);
const feedsStore = useFeedsStore();
const toastsStore = useToastsStore();

onMounted(() => {
  deleteFeedModal.value = new Modal(
    document.getElementById(`deleteFeedModal_${props.feed.id}`),
  );
});

onBeforeUnmount(() => {
  deleteFeedModal.value?.dispose();
});

function openDeleteFeedModal() {
  deleteFeedModal.value?.show();
}

function handleFeedDeleted() {
  emit("feed-deleted", props.feed.id);
}

function fetchFeed(feed) {
  feedsStore
    .fetch(feed.id)
    .then((response) => {
      toastsStore.push("Feed fetch enqueued. Task ID: " + response.task.id);
    })
    .catch((error) => {
      toastsStore.push("Error fetching feed: " + error, "error");
    });
}

function previewFeed(feed) {
  previewResult.value = null;
  previewError.value = null;
  previewing.value = true;
  feedsStore
    .testMISPFeedConnection(feed)
    .then((response) => {
      previewResult.value = response;
      previewOpen.value = true;
    })
    .catch((error) => {
      previewError.value =
        typeof error === "string" ? error : "Failed to connect to feed.";
      previewOpen.value = true;
    })
    .finally(() => {
      previewing.value = false;
    });
}
</script>

<style scoped>
.btn-toolbar {
  flex-wrap: nowrap !important;
}
</style>

<template>
  <div>
    <div class="btn-toolbar float-end" role="toolbar">
      <div
        v-if="actions.fetch"
        class="flex-wrap btn-group me-2"
        aria-label="Sync Actions"
      >
        <button
          type="button"
          class="btn btn-outline-primary btn-sm"
          data-placement="top"
          title="Fetch"
          @click="fetchFeed(feed)"
          :class="{ disabled: !feed.enabled }"
        >
          <font-awesome-icon icon="fa-solid fa-download" />
        </button>
        <button
          v-if="feed.source_format === 'misp'"
          type="button"
          class="btn btn-outline-primary btn-sm"
          title="Preview feed events"
          :disabled="previewing"
          @click="previewFeed(feed)"
        >
          <span
            v-if="previewing"
            class="spinner-border spinner-border-sm"
            role="status"
            aria-hidden="true"
          ></span>
          <font-awesome-icon v-else icon="fa-solid fa-magnifying-glass" />
        </button>
        <button
          v-else
          type="button"
          class="btn btn-outline-primary btn-sm"
          title="Preview (only available for MISP feeds)"
          disabled
        >
          <font-awesome-icon icon="fa-solid fa-magnifying-glass" />
        </button>
      </div>
      <div
        :class="{
          'btn-group-vertical': $isMobile,
          'btn-group me-2': !$isMobile,
        }"
        role="group"
        aria-label="Feed Actions"
      >
        <RouterLink
          v-if="actions.read"
          :to="`/feeds/${feed.id}`"
          class="btn btn-outline-primary btn-sm"
        >
          <font-awesome-icon icon="fa-solid fa-eye" />
        </RouterLink>
        <RouterLink
          v-if="actions.update"
          :to="`/feeds/update/${feed.id}`"
          class="btn btn-outline-primary btn-sm"
        >
          <font-awesome-icon icon="fa-solid fa-pen" />
        </RouterLink>
      </div>
      <div v-if="actions.delete" class="btn-group me-2" role="group">
        <button
          type="button"
          class="btn btn-danger btn-sm"
          @click="openDeleteFeedModal"
        >
          <font-awesome-icon icon="fa-solid fa-trash" />
        </button>
      </div>
    </div>
    <DeleteFeedModal
      :key="feed.id"
      :id="`deleteFeedModal_${feed.id}`"
      @feed-deleted="handleFeedDeleted"
      :modal="deleteFeedModal"
      :feed_id="feed.id"
    />
    <PreviewFeedModal
      v-if="previewOpen"
      :result="previewResult"
      :error="previewError"
      @close="previewOpen = false"
    />
  </div>
</template>
