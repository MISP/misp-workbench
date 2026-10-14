<script setup>
import { ref } from "vue";
import { storeToRefs } from "pinia";
import { useDetectionProfilesStore, useToastsStore } from "@/stores";
import Spinner from "@/components/misc/Spinner.vue";
import { router } from "@/router";

const profilesStore = useDetectionProfilesStore();
const toastsStore = useToastsStore();
const { profiles, status } = storeToRefs(profilesStore);
const counts = ref({});

function load() {
  profilesStore.getAll().then(() => {
    for (const p of profiles.value) {
      profilesStore
        .count(p.id)
        .then((r) => (counts.value = { ...counts.value, [p.id]: r.count }))
        .catch(() => {});
    }
  });
}
load();

function summary(rules) {
  const parts = [];
  if (rules.types?.length) parts.push(rules.types.join(", "));
  if (rules.to_ids) parts.push("IDS only");
  if (rules.min_score !== null && rules.min_score !== undefined)
    parts.push(`score ≥ ${rules.min_score}`);
  if (rules.max_age_days) parts.push(`seen ≤ ${rules.max_age_days}d ago`);
  if (rules.tlp_ceiling) parts.push(`≤ ${rules.tlp_ceiling}`);
  if (rules.exclude_warninglisted) parts.push("no warninglisted");
  if (rules.exclude_validation_issues) parts.push("no validation issues");
  if (rules.exclude_lists?.length)
    parts.push(
      `not on ${rules.exclude_lists.length} organisation list${rules.exclude_lists.length === 1 ? "" : "s"}`,
    );
  if (rules.sources?.length) parts.push(`only ${rules.sources.join(", ")}`);
  if (rules.exclude_sources?.length)
    parts.push(`not only ${rules.exclude_sources.join(", ")}`);
  if (rules.min_source_trust !== null && rules.min_source_trust !== undefined)
    parts.push(`trust ≥ ${rules.min_source_trust}`);
  if (rules.hit_expiry) {
    const windows = Object.entries(rules.hit_expiry.types || {}).map(
      ([type, days]) => `${type} ${days}d`,
    );
    if (rules.hit_expiry.days) windows.unshift(`${rules.hit_expiry.days}d`);
    parts.push(`hit within ${windows.join(", ")}`);
  }
  if (rules.require_approval) parts.push("approved only");
  else if (rules.exclude_rejected) parts.push("no rejected");
  return parts.join(" · ") || "everything";
}

// Open the profile's indicators in Explore, as an editable query.
async function explore(profile) {
  try {
    const { query, snapshot } = await profilesStore.query(profile.id);
    if (snapshot) {
      toastsStore.push(
        "The query lists the sources present now: ones added later aren't covered by it (they are by the profile).",
        "info",
      );
    }
    router.push({ path: "/explore", query: { q: query, tab: "indicators" } });
  } catch (error) {
    toastsStore.push(`${error}`, "danger");
  }
}

async function remove(profile) {
  if (!confirm(`Delete the profile "${profile.name}"?`)) return;
  try {
    await profilesStore.remove(profile.id);
    toastsStore.push(`Profile "${profile.name}" deleted.`, "success");
    load();
  } catch (error) {
    toastsStore.push(`${error}`, "danger");
  }
}
</script>

<template>
  <div class="card">
    <div
      class="card-header border-bottom d-flex justify-content-between align-items-center"
    >
      <h4 class="mb-0">Detection profiles</h4>
      <RouterLink to="/detection-profiles/add" class="btn btn-primary btn-sm"
        >+ New profile</RouterLink
      >
    </div>
    <div class="card-body">
      <p class="text-muted">
        What goes to each kind of security control, defined once and used by
        exports, feeds, sinks, lookups and restSearch.
      </p>
      <Spinner v-if="status.loading" />
      <div v-else-if="status.error" class="alert alert-danger">
        {{ status.error }}
      </div>
      <div v-else class="table-responsive">
        <table class="table align-middle">
          <thead>
            <tr>
              <th>name</th>
              <th>sends</th>
              <th>rules</th>
              <th class="text-end">matching now</th>
              <th class="text-end">actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="p in profiles" :key="p.id">
              <td>
                <RouterLink :to="`/detection-profiles/update/${p.id}`">{{
                  p.name
                }}</RouterLink>
                <span
                  v-if="p.auto_approve"
                  class="badge text-bg-success ms-2"
                  title="What it selects is approved without a review"
                  >auto-approve</span
                >
                <span
                  v-if="p.rules.require_approval"
                  class="badge text-bg-info ms-2"
                  title="Only approved indicators; the rest wait in the review queue"
                  >requires approval</span
                >
                <RouterLink
                  v-if="p.held"
                  :to="`/detection-profiles/${p.id}/changes`"
                  class="badge text-bg-warning ms-2 text-decoration-none"
                  title="Some changes are kept out of its outputs until approved"
                  >changes held</RouterLink
                >
                <div v-if="p.description" class="small text-muted">
                  {{ p.description }}
                </div>
              </td>
              <td>{{ p.granularity }}</td>
              <td class="small">{{ summary(p.rules) }}</td>
              <td class="text-end font-monospace">
                {{ counts[p.id]?.toLocaleString() ?? "…" }}
              </td>
              <td class="text-end text-nowrap">
                <button
                  class="btn btn-outline-secondary btn-sm me-1"
                  title="Open its indicators in Explore, as a query you can edit"
                  @click="explore(p)"
                >
                  Explore
                </button>
                <RouterLink
                  :to="`/detection-profiles/${p.id}/changes`"
                  class="btn btn-outline-secondary btn-sm me-1"
                  title="What its next run changes, and its recent runs"
                  >Changes</RouterLink
                >
                <RouterLink
                  :to="`/detection-profiles/update/${p.id}`"
                  class="btn btn-outline-primary btn-sm me-1"
                  >Edit</RouterLink
                >
                <button
                  class="btn btn-outline-danger btn-sm"
                  @click="remove(p)"
                >
                  Delete
                </button>
              </td>
            </tr>
            <tr v-if="!profiles.length">
              <td colspan="5" class="text-center text-muted py-4">
                No profiles yet.
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
