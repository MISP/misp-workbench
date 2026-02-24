<script setup>
import { storeToRefs } from "pinia";
import { RouterLink } from "vue-router";
import Spinner from "@/components/misc/Spinner.vue";
import { useFeedsStore } from "@/stores";
import FeedActions from "@/components/feeds/FeedActions.vue";

const feedsStore = useFeedsStore();
const { feeds, status } = storeToRefs(feedsStore);

feedsStore.getAll();

function handleFeedDeleted() {
  feedsStore.getAll();
}

function toggleEnable(feed) {
  feedsStore
    .toggleEnable(feed)
    .then(() => {
      feed.enabled = !feed.enabled;
    })
    .catch((errors) => (this.status.error = errors));
}
</script>

<template>
  <Spinner v-if="status.loading" />
  <div class="table-responsive-sm">
    <table v-show="!status.loading" class="table table-striped text-start">
      <thead>
        <tr>
          <th scope="col">feed</th>
          <th scope="col" v-if="!$isMobile">provider</th>
          <th scope="col" v-if="!$isMobile">format</th>
          <th scope="col" v-if="!$isMobile">source</th>
          <th scope="col" class="text-end">enabled</th>
          <th scope="col" class="text-end">actions</th>
        </tr>
      </thead>
      <tbody>
        <tr :key="feed.id" v-for="feed in feeds">
          <!-- Name + URL -->
          <td>
            <RouterLink
              :to="`/feeds/${feed.id}`"
              class="fw-semibold text-decoration-none"
            >
              {{ feed.name }}
            </RouterLink>
            <div
              class="text-muted small text-truncate"
              style="max-width: 320px"
              :title="feed.url"
            >
              {{ feed.url }}
            </div>
          </td>
          <td>{{ feed.provider }}</td>
          <td v-if="!$isMobile">{{ feed.source_format }}</td>
          <td v-if="!$isMobile">{{ feed.input_source }}</td>
          <td class="text-end">
            <div class="flex-wrap btn-group me-2" aria-label="Sync Actions">
              <button
                type="button"
                class="btn"
                @click="toggleEnable(feed)"
                :class="{
                  'btn-outline-success': feed.enabled,
                  'btn-outline-danger': !feed.enabled,
                }"
                data-toggle="tooltip"
                data-placement="top"
                title="Toggle feed"
              >
                <font-awesome-icon
                  v-if="feed.enabled"
                  icon="fa-solid fa-check"
                />
                <font-awesome-icon
                  v-if="!feed.enabled"
                  icon="fa-solid fa-xmark"
                />
              </button>
            </div>
          </td>
          <td class="text-end">
            <FeedActions :feed="feed" @feed-deleted="handleFeedDeleted" />
          </td>
        </tr>
      </tbody>
    </table>
    <div v-if="status.error" class="alert alert-danger" role="alert">
      {{ status.error }}
    </div>
  </div>
</template>
