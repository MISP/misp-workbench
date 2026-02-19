<script setup>
import { ref, onMounted, onUnmounted } from "vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import {
  faChevronDown,
  faChevronUp,
  faFloppyDisk,
  faXmark,
} from "@fortawesome/free-solid-svg-icons";

defineProps({
  savedSearches: { type: Array, default: () => [] },
  recentSearches: { type: Array, default: () => [] },
});

const emit = defineEmits(["select", "save", "delete", "forget"]);

const isOpen = ref(false);
const panelRef = ref(null);

function toggleOpen() {
  isOpen.value = !isOpen.value;
}

function _handleDocumentClick(e) {
  try {
    const el = panelRef.value;
    if (!el) return;
    if (isOpen.value && !el.contains(e.target)) {
      isOpen.value = false;
    }
  } catch (err) {
    console.error("Error handling document click:", err);
  }
}

onMounted(() => document.addEventListener("click", _handleDocumentClick));
onUnmounted(() => document.removeEventListener("click", _handleDocumentClick));
</script>

<style scoped>
.saved-searches-panel {
  position: sticky;
  top: 1rem;
  z-index: 1;
  width: 270px;
}

.saved-searches-panel .list-group {
  scrollbar-gutter: stable;
}

.card-header-sm {
  padding: 0.25rem 0.5rem;
}

.card {
  position: relative;
}

.card-body {
  position: absolute;
  top: 100%;
  width: 100%;
  z-index: 2;
  background: var(--bs-card-bg, #fff);
  border: var(--bs-card-border-width, 1px) solid
    var(--bs-card-border-color, rgba(0, 0, 0, 0.125));
  border-top: none;
  border-bottom-left-radius: var(--bs-card-border-radius);
  border-bottom-right-radius: var(--bs-card-border-radius);
}

.card-body .list-group-flush > .list-group-item:last-child {
  border-bottom-left-radius: var(--bs-card-border-radius);
  border-bottom-right-radius: var(--bs-card-border-radius);
}
</style>

<template>
  <div
    class="saved-searches-panel"
    ref="panelRef"
    role="dialog"
    aria-label="saved searches"
  >
    <div class="card">
      <div
        class="card-header card-header-sm d-flex justify-content-between align-items-center"
        role="button"
        tabindex="0"
        @click="toggleOpen"
        @keydown.enter.prevent="toggleOpen"
        @keydown.space.prevent="toggleOpen"
      >
        <div class="mt-1">
          <strong>search history</strong>
          <span class="text-muted ms-1">
            ({{ savedSearches.length + recentSearches.length }})
          </span>
        </div>
        <FontAwesomeIcon
          :icon="isOpen ? faChevronUp : faChevronDown"
          class="text-muted"
        />
      </div>

      <div class="card-body p-0" v-show="isOpen">
        <ul
          class="list-group list-group-flush"
          style="max-height: 60vh; overflow: auto"
          v-if="savedSearches.length > 0 || recentSearches.length > 0"
        >
          <li
            v-for="(term, idx) in savedSearches"
            :key="term + idx"
            class="list-group-item d-flex justify-content-between align-items-center"
          >
            <div
              class="text-truncate cursor-pointer text-console"
              :title="term"
              style="max-width: 220px"
              @click="emit('select', term)"
            >
              {{ term }}
            </div>
            <div class="btn-group btn-group-sm">
              <button class="btn text-secondary" @click="emit('delete', term)">
                <FontAwesomeIcon :icon="faXmark" />
              </button>
            </div>
          </li>
          <li
            v-for="(term, idx) in recentSearches"
            :key="term + idx"
            class="list-group-item d-flex justify-content-between align-items-center"
          >
            <div
              class="text-truncate cursor-pointer text-console"
              :title="term"
              style="max-width: 220px"
              @click="emit('select', term)"
            >
              {{ term }}
            </div>
            <div class="btn-group btn-group-sm">
              <button class="btn text-secondary" @click="emit('save', term)">
                <FontAwesomeIcon :icon="faFloppyDisk" />
              </button>
              <button class="btn text-secondary" @click="emit('forget', term)">
                <FontAwesomeIcon :icon="faXmark" />
              </button>
            </div>
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>
