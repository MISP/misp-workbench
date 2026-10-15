<script setup>
// Ctrl+K (⌘K): jump to any page, or straight to an event, attribute or
// object by uuid, or search a value in Explore.
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from "vue";
import { useRouter } from "vue-router";
import { storeToRefs } from "pinia";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import {
  faArrowRight,
  faBullseye,
  faCalendarDays,
  faCube,
  faFingerprint,
  faMagnifyingGlass,
} from "@fortawesome/free-solid-svg-icons";
import { useAuthStore } from "@/stores";
import { authHelper } from "@/helpers";
import { fetchWrapper } from "@/helpers/fetch-wrapper";
import { searchablePages } from "@/components/menu/menu";

const router = useRouter();
const { scopes } = storeToRefs(useAuthStore());
const can = (scope) => authHelper.hasScope(scopes.value || [], scope);

const isOpen = ref(false);
const query = ref("");
const activeIndex = ref(0);
const input = ref(null);
const found = ref([]);
const looking = ref(false);
let returnFocus = null;

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const API = import.meta.env.VITE_API_URL;

// What a uuid can be, and how to open it.
const KINDS = [
  {
    kind: "Event",
    scope: "events:read",
    icon: faCalendarDays,
    url: (uuid) => `${API}/events/${uuid}`,
    to: (uuid) => `/events/${uuid}`,
    title: (item) => item.info,
  },
  {
    kind: "Attribute",
    scope: "attributes:read",
    icon: faFingerprint,
    url: (uuid) => `${API}/attributes/${uuid}`,
    to: (uuid) => `/attributes/${uuid}`,
    title: (item) => `${item.type}: ${item.value}`,
  },
  {
    kind: "Object",
    scope: "objects:read",
    icon: faCube,
    url: (uuid) => `${API}/objects/${uuid}`,
    to: (uuid) => `/objects/${uuid}`,
    title: (item) => item.name,
  },
];

function matches(page, words) {
  const text =
    `${page.label} ${page.description} ${page.category}`.toLowerCase();
  return words.every((word) => text.includes(word));
}

function rank(page, term) {
  const label = page.label.toLowerCase();
  if (label.startsWith(term)) return 0;
  if (label.includes(term)) return 1;
  return 2;
}

const results = computed(() => {
  const term = query.value.trim();
  const lowered = term.toLowerCase();
  const words = lowered.split(/\s+/).filter(Boolean);
  const pages = searchablePages(scopes.value)
    .filter((page) => matches(page, words))
    .sort((a, b) => rank(a, lowered) - rank(b, lowered))
    .map((page) => ({
      id: `page-${page.id}`,
      icon: page.icon,
      label: page.label,
      detail: page.description,
      tag: page.category,
      to: page.to,
    }));
  const items = [...found.value, ...pages];
  if (term && !UUID.test(term)) {
    if (can("events:read")) {
      items.push({
        id: "search-explore",
        icon: faMagnifyingGlass,
        label: `Search “${term}” in Explore`,
        detail: "Events, attributes, indicators and correlations",
        to: { path: "/explore", query: { q: term } },
      });
    }
    if (can("attributes:read")) {
      items.push({
        id: "search-indicators",
        icon: faBullseye,
        label: `Find indicators matching “${term}”`,
        detail: "Each value once, with its sources and score",
        to: { path: "/explore", query: { q: term, tab: "indicators" } },
      });
    }
  }
  return items;
});

// A uuid: look it up as each kind the user may read.
let lookup = 0;
watch(query, async (value) => {
  activeIndex.value = 0;
  const term = value.trim();
  found.value = [];
  if (!UUID.test(term)) return;
  const uuid = term.toLowerCase();
  const id = ++lookup;
  looking.value = true;
  const hits = await Promise.all(
    KINDS.filter((k) => can(k.scope)).map((k) =>
      fetchWrapper
        .get(k.url(uuid))
        .then((item) => ({
          id: `${k.kind}-${uuid}`,
          icon: k.icon,
          label: `${k.kind}: ${k.title(item) || uuid}`,
          detail: uuid,
          tag: k.kind,
          to: k.to(uuid),
        }))
        .catch(() => null),
    ),
  );
  if (id !== lookup) return;
  looking.value = false;
  found.value = hits.filter(Boolean);
});

const emit = defineEmits(["opening"]);

async function open() {
  if (isOpen.value) return;
  emit("opening");
  returnFocus = document.activeElement;
  query.value = "";
  activeIndex.value = 0;
  isOpen.value = true;
  await nextTick();
  input.value?.focus();
}

function close() {
  isOpen.value = false;
  returnFocus?.focus?.();
}

function go(item) {
  if (!item) return;
  close();
  router.push(item.to).catch(() => {});
}

async function move(step) {
  const count = results.value.length;
  if (!count) return;
  activeIndex.value = (activeIndex.value + step + count) % count;
  await nextTick();
  document
    .getElementById(`switcher-${results.value[activeIndex.value].id}`)
    ?.scrollIntoView({ block: "nearest" });
}

// Tab stays in the dialog: there is one field, and the list follows it.
function onKeydown(event) {
  if (event.key === "ArrowDown") {
    event.preventDefault();
    move(1);
  } else if (event.key === "ArrowUp") {
    event.preventDefault();
    move(-1);
  } else if (event.key === "Enter") {
    event.preventDefault();
    go(results.value[activeIndex.value]);
  } else if (event.key === "Escape") {
    event.preventDefault();
    close();
  } else if (event.key === "Tab") {
    event.preventDefault();
  }
}

function onGlobalKeydown(event) {
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
    event.preventDefault();
    if (isOpen.value) close();
    else open();
  }
}

onMounted(() => window.addEventListener("keydown", onGlobalKeydown));
onUnmounted(() => window.removeEventListener("keydown", onGlobalKeydown));

defineExpose({ open, close });
</script>

<template>
  <Teleport to="body">
    <div v-if="isOpen" class="switcher-backdrop" @mousedown.self="close">
      <div
        class="switcher card shadow-lg"
        role="dialog"
        aria-modal="true"
        aria-label="Quick switcher"
      >
        <div class="d-flex align-items-center gap-2 px-3 border-bottom">
          <FontAwesomeIcon
            :icon="faMagnifyingGlass"
            class="text-body-secondary"
          />
          <input
            ref="input"
            v-model="query"
            class="form-control border-0 shadow-none py-3"
            type="text"
            role="combobox"
            aria-autocomplete="list"
            aria-expanded="true"
            aria-controls="switcher-results"
            :aria-activedescendant="
              results[activeIndex]
                ? `switcher-${results[activeIndex].id}`
                : undefined
            "
            placeholder="Jump to a page, paste a uuid, or search a value"
            autocomplete="off"
            spellcheck="false"
            @keydown="onKeydown"
          />
          <kbd class="small">Esc</kbd>
        </div>
        <ul
          id="switcher-results"
          class="list-unstyled mb-0 switcher-results"
          role="listbox"
          aria-label="Results"
        >
          <li
            v-for="(item, index) in results"
            :id="`switcher-${item.id}`"
            :key="item.id"
            role="option"
            :aria-selected="index === activeIndex ? 'true' : 'false'"
            class="switcher-item d-flex align-items-center gap-3 px-3 py-2"
            :class="{ active: index === activeIndex }"
            @mousemove="activeIndex = index"
            @click="go(item)"
          >
            <span class="switcher-icon" aria-hidden="true">
              <FontAwesomeIcon :icon="item.icon" fixed-width />
            </span>
            <span class="d-flex flex-column flex-grow-1 overflow-hidden">
              <span class="text-truncate">{{ item.label }}</span>
              <span class="small text-body-secondary text-truncate">{{
                item.detail
              }}</span>
            </span>
            <span
              v-if="item.tag"
              class="badge bg-body-tertiary text-body-secondary border"
              >{{ item.tag }}</span
            >
            <FontAwesomeIcon
              v-if="index === activeIndex"
              :icon="faArrowRight"
              class="text-body-secondary"
              aria-hidden="true"
            />
          </li>
          <li
            v-if="looking"
            class="px-3 py-3 text-body-secondary small"
            role="presentation"
          >
            Looking it up…
          </li>
          <li
            v-else-if="!results.length"
            class="px-3 py-3 text-body-secondary small"
            role="presentation"
          >
            Nothing matches “{{ query.trim() }}”.
          </li>
        </ul>
        <div
          class="px-3 py-2 border-top small text-body-secondary d-flex gap-3"
        >
          <span><kbd>↑</kbd> <kbd>↓</kbd> to move</span>
          <span><kbd>Enter</kbd> to open</span>
          <span><kbd>Esc</kbd> to close</span>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.switcher-backdrop {
  position: fixed;
  inset: 0;
  z-index: 1080;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: 10vh 1rem 1rem;
}
.switcher {
  width: 100%;
  max-width: 40rem;
  overflow: hidden;
}
.switcher-results {
  max-height: min(60vh, 28rem);
  overflow-y: auto;
}
.switcher-item {
  cursor: pointer;
  min-height: 44px;
}
.switcher-item.active {
  background: var(--bs-primary-bg-subtle);
}
.switcher-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  flex: 0 0 auto;
  border-radius: 0.375rem;
  background: var(--bs-tertiary-bg);
  color: var(--bs-primary);
}
kbd {
  background: var(--bs-tertiary-bg);
  color: var(--bs-secondary-color);
  border: 1px solid var(--bs-border-color);
}
</style>
