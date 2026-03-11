<script setup>
import { ref, computed, onMounted } from "vue";
import { useFeedsStore } from "@/stores";

const emit = defineEmits(["select"]);

const feedsStore = useFeedsStore();
const defaults = ref([]);
const search = ref("");
const loading = ref(false);

onMounted(async () => {
  loading.value = true;
  defaults.value = (await feedsStore.getDefaults()) ?? [];
  loading.value = false;
});

const supported = computed(() =>
  defaults.value.filter((f) => f.source_format !== "freetext"),
);

const filtered = computed(() => {
  const q = search.value.toLowerCase();
  if (!q) return supported.value;
  return supported.value.filter(
    (f) =>
      f.name.toLowerCase().includes(q) ||
      f.provider.toLowerCase().includes(q) ||
      f.url.toLowerCase().includes(q),
  );
});

const FORMAT_LABELS = {
  misp: "MISP",
  csv: "CSV",
  json: "JSON",
};

const FORMAT_CLASSES = {
  misp: "bg-primary",
  csv: "bg-success",
  json: "bg-info text-dark",
};
</script>

<template>
  <div>
    <div class="mb-2">
      <input
        v-model="search"
        type="search"
        class="form-control form-control-sm"
        placeholder="Search by name, provider or URL..."
        autofocus
      />
    </div>

    <div v-if="loading" class="text-center py-3 text-muted small">
      Loading...
    </div>

    <div
      v-else-if="filtered.length === 0"
      class="text-center py-3 text-muted small"
    >
      No feeds match your search.
    </div>

    <div v-else class="default-feed-list">
      <button
        v-for="feed in filtered"
        :key="feed.url"
        type="button"
        class="list-group-item list-group-item-action px-3 py-2"
        @click="emit('select', feed)"
      >
        <div class="d-flex align-items-center gap-2">
          <span
            class="badge"
            :class="FORMAT_CLASSES[feed.source_format] ?? 'bg-secondary'"
          >
            {{ FORMAT_LABELS[feed.source_format] ?? feed.source_format }}
          </span>
          <span class="fw-semibold text-truncate">{{ feed.name }}</span>
          <span
            class="text-muted small ms-auto text-truncate flex-shrink-0"
            style="max-width: 200px"
          >
            {{ feed.provider }}
          </span>
        </div>
      </button>
    </div>
  </div>
</template>

<style scoped>
.default-feed-list {
  max-height: 320px;
  overflow-y: auto;
  border: 1px solid var(--bs-border-color);
  border-radius: var(--bs-border-radius);
}
</style>
