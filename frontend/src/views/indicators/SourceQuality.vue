<script setup>
import { ref, computed } from "vue";
import { useIndicatorsStore } from "@/stores";
import Spinner from "@/components/misc/Spinner.vue";
import QualityRate from "@/components/indicators/QualityRate.vue";

const indicatorsStore = useIndicatorsStore();
const report = ref(null);
const error = ref(null);

indicatorsStore
  .sourceQuality()
  .then((r) => (report.value = r))
  .catch((e) => (error.value = e));

const sections = computed(() =>
  report.value
    ? [
        {
          title: "Sources",
          help: "Feeds, MISP servers and locally created events.",
          rows: report.value.sources,
        },
        {
          title: "Organisations",
          help: "The organisations that created the events.",
          rows: report.value.organisations,
        },
      ]
    : [],
);

function link(row) {
  if (row.kind === "feed") return `/feeds/${row.id}`;
  if (row.kind === "server") return `/servers/${row.id}`;
  if (row.kind === "organisation") return `/organisations/${row.id}`;
  return null;
}

function trust(row) {
  const parts = [];
  if (row.score_modifier)
    parts.push(`${row.score_modifier > 0 ? "+" : ""}${row.score_modifier}`);
  if (row.score_cap !== null) parts.push(`cap ${row.score_cap}`);
  return parts.join(", ") || "—";
}
</script>

<template>
  <div class="card">
    <div
      class="card-header border-bottom d-flex justify-content-between align-items-center"
    >
      <h4 class="mb-0">Source quality</h4>
      <RouterLink to="/indicators" class="small">indicators</RouterLink>
    </div>
    <div class="card-body">
      <p class="text-muted">
        How each source's indicators hold up: how many it reports, how many
        nobody else does, and how many were sighted or reported benign in the
        last {{ report?.window_days ?? 30 }} days. Set a source's score modifier
        and cap on its own page.
        <template v-if="report">
          Adaptive trust is
          <strong>{{ report.adaptive_trust ? "on" : "off" }}</strong
          >{{
            report.adaptive_trust
              ? ": false-positive rates lower sources' trust."
              : ": the penalty shown is what it would take off."
          }}
        </template>
      </p>

      <Spinner v-if="!report && !error" />
      <div v-else-if="error" class="alert alert-danger">{{ error }}</div>
      <template v-else>
        <section v-for="section in sections" :key="section.title" class="mb-4">
          <h5 class="mb-1">{{ section.title }}</h5>
          <p class="text-muted small mb-2">{{ section.help }}</p>
          <div class="table-responsive">
            <table class="table table-sm align-middle">
              <thead>
                <tr>
                  <th>name</th>
                  <th class="text-end">indicators</th>
                  <th class="text-end" title="Also reported by others">
                    overlap
                  </th>
                  <th>overlaps most with</th>
                  <th class="text-end" title="Sighted within the window">
                    hit rate
                  </th>
                  <th
                    class="text-end"
                    title="Reported benign within the window"
                  >
                    false positives
                  </th>
                  <th class="text-end">avg score</th>
                  <th
                    class="text-end"
                    title="Score below the decayed threshold"
                  >
                    decayed
                  </th>
                  <th>trust</th>
                  <th
                    class="text-end"
                    title="What adaptive trust takes off for false positives"
                  >
                    adaptive
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in section.rows" :key="row.key">
                  <td>
                    <RouterLink v-if="link(row)" :to="link(row)">{{
                      row.name
                    }}</RouterLink>
                    <span v-else>{{ row.name }}</span>
                    <span class="text-muted small ms-1">{{ row.kind }}</span>
                  </td>
                  <td class="text-end font-monospace">
                    {{ row.indicators.toLocaleString() }}
                  </td>
                  <td class="text-end">
                    <QualityRate :value="row.overlap_rate" good="none" />
                  </td>
                  <td class="small">
                    <span
                      v-for="other in row.top_overlaps.slice(0, 3)"
                      :key="other.key"
                      class="me-2"
                      >{{ other.name }} ({{ other.indicators }})</span
                    >
                  </td>
                  <td class="text-end">
                    <QualityRate :value="row.hit_rate" />
                  </td>
                  <td class="text-end">
                    <QualityRate :value="row.false_positive_rate" good="low" />
                  </td>
                  <td class="text-end font-monospace">
                    {{ row.average_score ?? "—" }}
                  </td>
                  <td class="text-end">
                    <QualityRate :value="row.decayed_rate" good="none" />
                  </td>
                  <td class="small">{{ trust(row) }}</td>
                  <td class="text-end font-monospace">
                    <span
                      v-if="row.adaptive_penalty"
                      :class="{ 'text-muted': !report.adaptive_trust }"
                      >−{{ row.adaptive_penalty }}</span
                    >
                    <span v-else class="text-muted">—</span>
                  </td>
                </tr>
                <tr v-if="!section.rows.length">
                  <td colspan="10" class="text-center text-muted py-3">
                    No indicators yet.
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      </template>
    </div>
  </div>
</template>
