<script setup>
import { ref, computed } from "vue";
import { useDetectionProfilesStore } from "@/stores";

// How much of what a saved profile selects sensors actually hit, per source.
const props = defineProps({ profileId: { type: Number, required: true } });

const profilesStore = useDetectionProfilesStore();
const report = ref(null);
const error = ref(null);

profilesStore
  .hits(props.profileId)
  .then((r) => (report.value = r))
  .catch((e) => (error.value = e));

const percent = (part, whole) =>
  whole ? `${Math.round((part / whole) * 100)}%` : "0%";
const sources = computed(() =>
  (report.value?.by_source || []).filter((s) => s.members || s.expired),
);
</script>

<template>
  <div class="border rounded p-3 mb-3">
    <div class="fw-semibold small mb-2">Hits, as saved</div>
    <div v-if="error" class="text-danger small">{{ error }}</div>
    <div v-else-if="!report" class="text-muted small">Counting…</div>
    <template v-else>
      <p class="small mb-2" id="profile-hits-summary">
        Of <strong>{{ report.members.toLocaleString() }}</strong> members,
        <strong>{{ report.never_hit.toLocaleString() }}</strong>
        ({{ percent(report.never_hit, report.members) }}) were never hit and
        <strong>{{ report.hit_recently.toLocaleString() }}</strong>
        were hit in the last {{ report.window_days }} days.
        <template v-if="report.expiry">
          Hit-rate expiry leaves out
          <strong>{{ report.expired.toLocaleString() }}</strong> more.
        </template>
      </p>
      <div v-if="sources.length" class="table-responsive">
        <table class="table table-sm align-middle mb-0 small">
          <thead>
            <tr>
              <th>source</th>
              <th class="text-end">members</th>
              <th class="text-end">never hit</th>
              <th v-if="report.expiry" class="text-end">expired</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="s in sources" :key="s.key">
              <td>
                {{ s.name }}
                <span v-if="s.name !== s.key" class="text-muted">{{
                  s.key
                }}</span>
              </td>
              <td class="text-end font-monospace">
                {{ s.members.toLocaleString() }}
              </td>
              <td class="text-end font-monospace">
                {{ s.never_hit.toLocaleString() }}
                <span class="text-muted">{{
                  percent(s.never_hit, s.members)
                }}</span>
              </td>
              <td v-if="report.expiry" class="text-end font-monospace">
                {{ s.expired.toLocaleString() }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </div>
</template>
