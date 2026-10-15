<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from "vue";
import { storeToRefs } from "pinia";
import {
  useIndicatorReviewsStore,
  useAuthStore,
  useToastsStore,
} from "@/stores";
import { authHelper } from "@/helpers";
import Spinner from "@/components/misc/Spinner.vue";
import Timestamp from "@/components/misc/Timestamp.vue";
import Pagination from "@/components/misc/Pagination.vue";
import ScoreBadge from "@/components/indicators/ScoreBadge.vue";
import IndicatorDetails from "@/components/indicators/IndicatorDetails.vue";
import IndicatorEnrichment from "@/components/indicators/IndicatorEnrichment.vue";

const reviewsStore = useIndicatorReviewsStore();
const authStore = useAuthStore();
const toastsStore = useToastsStore();
const { summary, page, status } = storeToRefs(reviewsStore);
const { scopes } = storeToRefs(authStore);

const canReview = computed(() =>
  authHelper.hasScope(scopes.value, "indicators:review"),
);

const TABS = ["pending", "snoozed", "approved", "rejected"];
const SNOOZES = [1, 7, 30];
const SIZE = 50;

const tab = ref("pending");
const currentPage = ref(1);
const filters = ref({
  q: "",
  type: "",
  profile_id: "",
  source: "",
  min_score: null,
  max_score: null,
  sort: "score",
});
const selected = ref(new Set());
const cursor = ref(0);
const expanded = ref(null);
const history = ref({});
const rejecting = ref(null);
const showHelp = ref(false);

const rowId = (item) => item.uuid ?? item.indicator_uuid;
const columns = computed(
  () => (tab.value === "pending" ? 6 : 5) + (canReview.value ? 1 : 0),
);

// The value as a quoted Explore query.
const exploreQuery = (value) =>
  `"${String(value).replace(/["\\]/g, (c) => `\\${c}`)}"`;
const items = computed(() => page.value.items || []);
const hasNextPage = computed(
  () => currentPage.value * SIZE < (page.value.total || 0),
);

function load() {
  const params =
    tab.value === "pending"
      ? { ...filters.value, page: currentPage.value, size: SIZE }
      : { q: filters.value.q, page: currentPage.value, size: SIZE };
  return reviewsStore.load(tab.value, params).then(() => {
    cursor.value = Math.min(cursor.value, Math.max(items.value.length - 1, 0));
  });
}

function refresh() {
  reviewsStore.getSummary();
  return load();
}

function apply() {
  currentPage.value = 1;
  selected.value = new Set();
  cursor.value = 0;
  load();
}

function goTo(delta) {
  currentPage.value += delta;
  selected.value = new Set();
  cursor.value = 0;
  load();
}

watch(tab, () => {
  expanded.value = null;
  apply();
});

function sourceLabel(source) {
  return source.type === "feed" || source.type === "server"
    ? `${source.type}: ${source.name}`
    : source.name || source.type;
}

// ── Selection ──────────────────────────────────────────────────────────────

function toggleSelected(item) {
  const next = new Set(selected.value);
  const id = rowId(item);
  if (next.has(id)) next.delete(id);
  else next.add(id);
  selected.value = next;
}

const allSelected = computed(
  () =>
    items.value.length > 0 &&
    items.value.every((i) => selected.value.has(rowId(i))),
);

function toggleAll() {
  selected.value = allSelected.value
    ? new Set()
    : new Set(items.value.map(rowId));
}

function toggleExpanded(item) {
  const id = rowId(item);
  expanded.value = expanded.value === id ? null : id;
  if (expanded.value && !history.value[id]) {
    reviewsStore
      .detail(id)
      .then((d) => (history.value = { ...history.value, [id]: d.history }))
      .catch(() => {});
  }
}

// What an action applies to: the selection, or else the row under the cursor.
function targets() {
  if (selected.value.size) return [...selected.value];
  const item = items.value[cursor.value];
  return item ? [rowId(item)] : [];
}

// ── Decisions ─────────────────────────────────────────────────────────────

const VERBS = {
  approve: "Approved",
  reject: "Rejected",
  snooze: "Snoozed",
  reopen: "Reopened",
};

async function decide(action, ids, extra = {}) {
  if (!canReview.value || !ids.length) return;
  try {
    const result = await reviewsStore.decide(ids, action, extra);
    toastsStore.push(
      `${VERBS[action]} ${result.decided} indicator${result.decided === 1 ? "" : "s"}.`,
      "success",
    );
    selected.value = new Set();
    expanded.value = null;
    history.value = {};
    await refresh();
  } catch (error) {
    toastsStore.push(`${error}`, "danger");
  }
}

function approve(ids = targets()) {
  decide("approve", ids);
}

function snooze(days, ids = targets()) {
  decide("snooze", ids, { snooze_days: days });
}

function reopen(ids = targets()) {
  decide("reopen", ids);
}

function startReject(ids = targets()) {
  if (!canReview.value || !ids.length) return;
  rejecting.value = { ids, reason: "", warninglist: false };
}

function confirmReject() {
  const { ids, reason, warninglist } = rejecting.value;
  rejecting.value = null;
  decide("reject", ids, { reason: reason.trim() || null, warninglist });
}

// ── Keyboard ──────────────────────────────────────────────────────────────

const SHORTCUTS = [
  ["j / ↓", "next indicator"],
  ["k / ↑", "previous indicator"],
  ["x", "select or unselect it"],
  ["shift + x", "select or unselect the page"],
  ["enter / o", "show or hide its context"],
  ["a", "approve"],
  ["r", "reject…"],
  ["s", "snooze for 7 days"],
  ["u", "reopen (decided tabs)"],
  ["1 – 4", "switch tab"],
  ["?", "these shortcuts"],
];

// Shortcuts stay off while typing; a ticked checkbox keeps focus but takes
// no text, so it doesn't count.
function typing(event) {
  const el = event.target;
  if (!el) return false;
  if (el.tagName === "INPUT")
    return !["checkbox", "radio", "button"].includes(el.type);
  return el.isContentEditable || ["TEXTAREA", "SELECT"].includes(el.tagName);
}

function onKey(event) {
  if (event.metaKey || event.ctrlKey || event.altKey) return;
  if (rejecting.value) {
    if (event.key === "Escape") rejecting.value = null;
    return;
  }
  if (typing(event)) return;
  const item = items.value[cursor.value];
  const actions = {
    j: () =>
      (cursor.value = Math.min(cursor.value + 1, items.value.length - 1)),
    ArrowDown: () =>
      (cursor.value = Math.min(cursor.value + 1, items.value.length - 1)),
    k: () => (cursor.value = Math.max(cursor.value - 1, 0)),
    ArrowUp: () => (cursor.value = Math.max(cursor.value - 1, 0)),
    x: () => item && toggleSelected(item),
    X: () => toggleAll(),
    Enter: () => item && toggleExpanded(item),
    o: () => item && toggleExpanded(item),
    a: () => tab.value !== "approved" && approve(),
    r: () => tab.value !== "rejected" && startReject(),
    s: () => tab.value !== "snoozed" && snooze(7),
    u: () => tab.value !== "pending" && reopen(),
    "?": () => (showHelp.value = !showHelp.value),
    Escape: () => {
      selected.value = new Set();
      showHelp.value = false;
    },
    1: () => (tab.value = TABS[0]),
    2: () => (tab.value = TABS[1]),
    3: () => (tab.value = TABS[2]),
    4: () => (tab.value = TABS[3]),
  };
  const run = actions[event.key];
  if (!run) return;
  event.preventDefault();
  run();
}

watch(cursor, (i) => {
  document
    .getElementById(`review-row-${i}`)
    ?.scrollIntoView({ block: "nearest" });
});

onMounted(() => window.addEventListener("keydown", onKey));
onBeforeUnmount(() => window.removeEventListener("keydown", onKey));

refresh();
</script>

<template>
  <div class="card">
    <div
      class="card-header border-bottom d-flex justify-content-between align-items-center"
    >
      <h4 class="mb-0">Review queue</h4>
      <button
        type="button"
        class="btn btn-outline-secondary btn-sm"
        title="Keyboard shortcuts (?)"
        @click="showHelp = !showHelp"
      >
        shortcuts
      </button>
    </div>
    <div class="card-body">
      <p class="text-muted">
        Indicators a profile requiring approval would send, waiting for an
        analyst. Approved ones go out; rejected ones never do, whichever source
        reports them again.
        <template v-if="summary">
          <template v-if="summary.requiring_profiles.length">
            Requiring approval:
            <RouterLink
              v-for="(p, i) in summary.requiring_profiles"
              :key="p.id"
              :to="`/detection-profiles/update/${p.id}`"
              >{{ p.name
              }}{{
                i < summary.requiring_profiles.length - 1 ? ", " : ""
              }}</RouterLink
            >.
          </template>
          <template v-if="summary.auto_approve_profiles.length">
            Approved automatically:
            <RouterLink
              v-for="(p, i) in summary.auto_approve_profiles"
              :key="p.id"
              :to="`/detection-profiles/update/${p.id}`"
              >{{ p.name
              }}{{
                i < summary.auto_approve_profiles.length - 1 ? ", " : ""
              }}</RouterLink
            >.
          </template>
        </template>
      </p>
      <div
        v-if="summary && !summary.requiring_profiles.length"
        class="alert alert-info"
      >
        No detection profile requires approval yet, so nothing waits here. Turn
        on <em>Require approval</em> on a
        <RouterLink to="/detection-profiles">profile</RouterLink> to review what
        it sends.
      </div>

      <div v-if="showHelp" class="alert alert-secondary small">
        <div class="d-flex justify-content-between">
          <strong>Keyboard shortcuts</strong>
          <button
            type="button"
            class="btn-close"
            aria-label="Close"
            @click="showHelp = false"
          ></button>
        </div>
        <div class="row">
          <div
            v-for="[key, what] in SHORTCUTS"
            :key="key"
            class="col-6 col-md-4"
          >
            <kbd>{{ key }}</kbd> {{ what }}
          </div>
        </div>
        <div class="mt-1 text-muted">
          Actions apply to the selected indicators, or to the highlighted one.
        </div>
      </div>

      <!-- One row on a phone too: it scrolls rather than wraps. -->
      <ul class="nav nav-tabs flex-nowrap overflow-x-auto overflow-y-hidden">
        <li v-for="t in TABS" :key="t" class="nav-item">
          <a
            href="#"
            class="nav-link text-nowrap"
            :class="{ active: tab === t }"
            @click.prevent="tab = t"
            >{{ t }}
            <span v-if="summary" class="badge text-bg-secondary ms-1">{{
              summary[t].toLocaleString()
            }}</span></a
          >
        </li>
      </ul>

      <!-- What the tabs switch, framed so the active tab opens onto it. -->
      <div class="border border-top-0 rounded-bottom p-3">
        <form class="row g-2 align-items-center mb-3" @submit.prevent="apply">
          <div
            :class="tab === 'pending' ? 'col-12 col-md-3' : 'col-12 col-md-6'"
          >
            <input
              class="form-control font-monospace"
              v-model="filters.q"
              :placeholder="
                tab === 'pending' ? 'value, or a query' : 'part of the value'
              "
              aria-label="Search"
            />
          </div>
          <template v-if="tab === 'pending'">
            <div class="col-6 col-md-2">
              <select
                class="form-select"
                v-model="filters.profile_id"
                aria-label="Profile"
                @change="apply"
              >
                <option value="">every profile</option>
                <option
                  v-for="p in summary?.requiring_profiles || []"
                  :key="p.id"
                  :value="p.id"
                >
                  {{ p.name }}
                </option>
              </select>
            </div>
            <div class="col-6 col-md-2">
              <input
                class="form-control"
                v-model="filters.type"
                placeholder="type (ip-dst)"
                aria-label="Type"
              />
            </div>
            <div class="col-6 col-md-1">
              <input
                class="form-control"
                v-model="filters.source"
                placeholder="feed:3"
                aria-label="Source"
                title="Only indicators from this source (feed:3, server:2, local)"
              />
            </div>
            <div class="col-3 col-md-1">
              <input
                class="form-control"
                type="number"
                min="0"
                max="100"
                v-model.number="filters.min_score"
                placeholder="min"
                aria-label="Minimum score"
              />
            </div>
            <div class="col-3 col-md-1">
              <input
                class="form-control"
                type="number"
                min="0"
                max="100"
                v-model.number="filters.max_score"
                placeholder="max"
                aria-label="Maximum score"
              />
            </div>
            <div class="col-6 col-md-1">
              <select
                class="form-select"
                v-model="filters.sort"
                aria-label="Sort"
                @change="apply"
              >
                <option value="score">score</option>
                <option value="last_seen">last seen</option>
                <option value="first_seen">first seen</option>
                <option value="event_count">events</option>
              </select>
            </div>
          </template>
          <div class="col-6 col-md-1 text-end">
            <button class="btn btn-outline-primary w-100" type="submit">
              Filter
            </button>
          </div>
        </form>

        <div
          v-if="canReview"
          class="review-actions d-flex flex-wrap align-items-center gap-2 mb-2 p-2 rounded bg-body-tertiary"
        >
          <span class="small text-muted me-2">
            {{
              selected.size
                ? `${selected.size} selected`
                : "Select indicators, or act on the highlighted one:"
            }}
          </span>
          <button
            v-if="tab !== 'approved'"
            type="button"
            class="btn btn-sm btn-success"
            :disabled="status.deciding || !items.length"
            title="Approve (a)"
            @click="approve()"
          >
            Approve
          </button>
          <button
            v-if="tab !== 'rejected'"
            type="button"
            class="btn btn-sm btn-outline-danger"
            :disabled="status.deciding || !items.length"
            title="Reject (r)"
            @click="startReject()"
          >
            Reject…
          </button>
          <div v-if="tab !== 'snoozed'" class="btn-group btn-group-sm">
            <button
              v-for="days in SNOOZES"
              :key="days"
              type="button"
              class="btn btn-outline-secondary"
              :disabled="status.deciding || !items.length"
              :title="
                days === 7 ? 'Snooze for 7 days (s)' : `Snooze for ${days} days`
              "
              @click="snooze(days)"
            >
              snooze {{ days }}d
            </button>
          </div>
          <button
            v-if="tab !== 'pending'"
            type="button"
            class="btn btn-sm btn-outline-primary"
            :disabled="status.deciding || !items.length"
            title="Back to the queue (u)"
            @click="reopen()"
          >
            Reopen
          </button>
          <span class="ms-auto small text-muted"> <kbd>?</kbd> shortcuts </span>
        </div>

        <Spinner v-if="status.loading" />
        <div v-else-if="status.error" class="alert alert-danger">
          {{ status.error }}
        </div>
        <template v-else>
          <div class="text-muted small mb-2">
            {{ page.total.toLocaleString() }}
            {{ tab === "pending" ? "waiting" : tab }}
          </div>
          <div class="table-responsive">
            <table class="table table-hover align-middle review-table">
              <thead>
                <tr>
                  <th v-if="canReview" style="width: 1%">
                    <input
                      type="checkbox"
                      class="form-check-input"
                      aria-label="Select the page"
                      :checked="allSelected"
                      @change="toggleAll"
                    />
                  </th>
                  <template v-if="tab === 'pending'">
                    <th>score</th>
                    <th>value</th>
                    <th class="d-none d-md-table-cell">type</th>
                    <th class="d-none d-xl-table-cell">sources</th>
                    <th class="d-none d-lg-table-cell">waiting for</th>
                    <th class="d-none d-lg-table-cell">last seen</th>
                  </template>
                  <template v-else>
                    <th>value</th>
                    <th class="d-none d-md-table-cell">type</th>
                    <th class="d-none d-md-table-cell">
                      {{ tab === "snoozed" ? "until" : "reason" }}
                    </th>
                    <th class="d-none d-lg-table-cell">by</th>
                    <th class="d-none d-lg-table-cell">decided</th>
                  </template>
                </tr>
              </thead>
              <tbody>
                <template v-for="(item, i) in items" :key="rowId(item)">
                  <tr
                    :id="`review-row-${i}`"
                    role="button"
                    :class="{
                      'table-active': cursor === i,
                      'review-cursor': cursor === i,
                    }"
                    @click="
                      cursor = i;
                      toggleExpanded(item);
                    "
                  >
                    <td v-if="canReview" @click.stop>
                      <input
                        type="checkbox"
                        class="form-check-input"
                        :aria-label="`Select ${item.value}`"
                        :checked="selected.has(rowId(item))"
                        @change="toggleSelected(item)"
                      />
                    </td>
                    <template v-if="tab === 'pending'">
                      <td>
                        <ScoreBadge
                          :score="item.score"
                          :breakdown="item.score_breakdown"
                        />
                      </td>
                      <td class="review-value">
                        <span
                          v-for="issue in item.validation_issues || []"
                          :key="issue"
                          class="badge text-bg-danger me-1"
                          >{{ issue }}</span
                        >
                        <span
                          v-if="item.warninglist_hits.length"
                          class="badge text-bg-warning me-1"
                          :title="item.warninglist_hits.join(', ')"
                          >warninglist</span
                        >
                        <span
                          v-if="item.review?.status === 'snoozed'"
                          class="badge text-bg-light border me-1"
                          title="Snoozed before; the snooze is over"
                          >was snoozed</span
                        >
                        <span class="font-monospace text-break">{{
                          item.value
                        }}</span>
                        <!-- On a phone, what the hidden columns would say. -->
                        <div
                          class="d-lg-none small text-body-secondary d-flex flex-wrap align-items-center column-gap-2 row-gap-1 mt-1"
                        >
                          <span class="d-md-none">{{ item.type }}</span>
                          <span
                            v-for="p in item.pending_for"
                            :key="p.id"
                            class="badge text-bg-info"
                            >{{ p.name }}</span
                          >
                          <span v-if="item.last_seen"
                            >last seen <Timestamp :timestamp="item.last_seen"
                          /></span>
                        </div>
                      </td>
                      <td class="d-none d-md-table-cell text-nowrap">
                        {{ item.type }}
                      </td>
                      <td class="d-none d-xl-table-cell">
                        <span
                          v-for="source in item.sources.slice(0, 3)"
                          :key="`${source.type}-${source.id}-${source.name}`"
                          class="badge text-bg-secondary me-1"
                          >{{ sourceLabel(source) }}</span
                        >
                        <span
                          v-if="item.sources.length > 3"
                          class="text-muted small"
                          >+{{ item.sources.length - 3 }}</span
                        >
                      </td>
                      <td class="d-none d-lg-table-cell">
                        <span
                          v-for="p in item.pending_for"
                          :key="p.id"
                          class="badge text-bg-info me-1"
                          >{{ p.name }}</span
                        >
                      </td>
                      <td class="d-none d-lg-table-cell small">
                        <Timestamp :timestamp="item.last_seen" />
                      </td>
                    </template>
                    <template v-else>
                      <td class="review-value">
                        <span
                          v-if="item.warninglisted"
                          class="badge text-bg-warning me-1"
                          title="Also on the Rejected in review warninglist"
                          >warninglisted</span
                        >
                        <span class="font-monospace text-break">{{
                          item.value
                        }}</span>
                        <div
                          class="d-lg-none small text-body-secondary d-flex flex-wrap column-gap-2 mt-1"
                        >
                          <span class="d-md-none">{{ item.type }}</span>
                          <span v-if="tab === 'snoozed'" class="d-md-none"
                            >until <Timestamp :timestamp="item.snoozed_until"
                          /></span>
                          <span
                            v-else-if="item.reason"
                            class="d-md-none text-break"
                            >{{ item.reason }}</span
                          >
                          <span
                            >decided <Timestamp :timestamp="item.decided_at" />
                            <template
                              v-if="item.user_email || item.user_organisation"
                              >by
                              {{
                                item.user_email || item.user_organisation
                              }}</template
                            ></span
                          >
                        </div>
                      </td>
                      <td class="d-none d-md-table-cell text-nowrap">
                        {{ item.type }}
                      </td>
                      <td class="d-none d-md-table-cell small">
                        <Timestamp
                          v-if="tab === 'snoozed'"
                          :timestamp="item.snoozed_until"
                        />
                        <span v-else class="text-break">{{
                          item.reason || "—"
                        }}</span>
                      </td>
                      <td class="d-none d-lg-table-cell small">
                        {{ item.user_email || item.user_organisation || "—" }}
                      </td>
                      <td class="d-none d-lg-table-cell small">
                        <Timestamp :timestamp="item.decided_at" />
                      </td>
                    </template>
                  </tr>
                  <tr v-if="expanded === rowId(item)">
                    <!-- max-width: 0: the details fit the row, never widen it. -->
                    <td
                      :colspan="columns"
                      class="bg-body-tertiary"
                      style="max-width: 0"
                    >
                      <template v-if="tab === 'pending'">
                        <IndicatorDetails :indicator="item" />
                        <hr class="my-2" />
                        <IndicatorEnrichment :indicator="item" />
                      </template>
                      <div class="small mt-2">
                        <strong>decisions</strong>
                        <span
                          v-if="!(history[rowId(item)] || []).length"
                          class="text-muted ms-2"
                          >none yet</span
                        >
                        <ul class="list-unstyled mb-0">
                          <li
                            v-for="(h, j) in history[rowId(item)] || []"
                            :key="j"
                          >
                            <Timestamp :timestamp="h.at" /> ·
                            <strong>{{ h.action }}</strong>
                            by
                            {{
                              h.user_email ||
                              h.user_organisation ||
                              "someone since removed"
                            }}
                            <span v-if="h.reason" class="text-muted"
                              >— {{ h.reason }}</span
                            >
                            <span
                              v-if="h.warninglisted"
                              class="badge text-bg-warning ms-1"
                              >warninglisted</span
                            >
                          </li>
                        </ul>
                        <RouterLink
                          :to="{
                            path: '/explore',
                            query: { q: exploreQuery(item.value) },
                          }"
                          class="d-inline-block mt-1"
                          @click.stop
                          >find in Explore</RouterLink
                        >
                      </div>
                    </td>
                  </tr>
                </template>
                <tr v-if="!items.length">
                  <td :colspan="columns" class="text-center text-muted py-4">
                    {{
                      tab === "pending"
                        ? "Nothing waiting for a review."
                        : `No ${tab} indicators.`
                    }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <Pagination
            :currentPage="currentPage"
            :hasPrevPage="currentPage > 1"
            :hasNextPage="hasNextPage"
            @prevPageClick="goTo(-1)"
            @nextPageClick="goTo(1)"
          />
        </template>
      </div>
    </div>

    <template v-if="rejecting">
      <div
        class="modal d-block"
        tabindex="-1"
        role="dialog"
        aria-labelledby="reject-title"
        @click.self="rejecting = null"
      >
        <div class="modal-dialog">
          <form class="modal-content" @submit.prevent="confirmReject">
            <div class="modal-header">
              <h5 id="reject-title" class="modal-title">
                Reject {{ rejecting.ids.length }} indicator{{
                  rejecting.ids.length === 1 ? "" : "s"
                }}
              </h5>
              <button
                type="button"
                class="btn-close"
                aria-label="Close"
                @click="rejecting = null"
              ></button>
            </div>
            <div class="modal-body">
              <label for="reject-reason" class="form-label">Why</label>
              <textarea
                id="reject-reason"
                v-model="rejecting.reason"
                class="form-control"
                rows="2"
                placeholder="e.g. shared hosting, sinkhole, internal range"
                autofocus
              ></textarea>
              <div class="form-check mt-3">
                <input
                  id="reject-warninglist"
                  v-model="rejecting.warninglist"
                  class="form-check-input"
                  type="checkbox"
                />
                <label class="form-check-label" for="reject-warninglist"
                  >Also add to the
                  <em>Rejected in review</em> warninglist</label
                >
                <div class="form-text">
                  The value is flagged as warninglisted everywhere, for every
                  profile and output, and scores lower.
                </div>
              </div>
            </div>
            <div class="modal-footer">
              <button
                type="button"
                class="btn btn-outline-secondary"
                @click="rejecting = null"
              >
                Cancel
              </button>
              <button type="submit" class="btn btn-danger">Reject</button>
            </div>
          </form>
        </div>
      </div>
      <div class="modal-backdrop show"></div>
    </template>
  </div>
</template>

<style scoped>
.review-cursor > td:first-child {
  box-shadow: inset 3px 0 0 var(--bs-primary);
}
/* The value takes the room the shown columns leave and wraps inside it,
   rather than squeezed a character per line on a phone. */
.review-value {
  width: 100%;
  max-width: 0;
}
.review-actions {
  position: sticky;
  top: 0;
  z-index: 2;
}
</style>
