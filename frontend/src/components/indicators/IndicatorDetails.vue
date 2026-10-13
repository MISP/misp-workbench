<script setup>
import { storeToRefs } from "pinia";
import Timestamp from "@/components/misc/Timestamp.vue";
import { useLocalWarninglistsStore } from "@/stores";

// Everything an indicator carries: how its score was reached, where it comes
// from, its tags, sightings and the warninglists it hits.
defineProps({ indicator: { type: Object, required: true } });

// Organisations' lists are named when they're yours (or for admins).
const localListsStore = useLocalWarninglistsStore();
const { byId: localLists } = storeToRefs(localListsStore);
localListsStore.ensureLoaded();

function sourceLabel(source) {
  return source.type === "feed" || source.type === "server"
    ? `${source.type}: ${source.name}`
    : source.name || source.type;
}
</script>

<template>
  <dl class="row small mb-0">
    <template v-if="indicator.score !== null">
      <dt class="col-sm-2">score</dt>
      <dd class="col-sm-10">
        <strong>{{ indicator.score }}</strong> / 100
        <ul class="list-unstyled mb-0">
          <li
            v-for="component in indicator.score_breakdown"
            :key="component.factor"
          >
            <span
              class="font-monospace d-inline-block text-end me-2"
              style="min-width: 3em"
              >{{
                component.points > 0 && component.factor !== "base" ? "+" : ""
              }}{{ component.points }}</span
            >{{ component.factor }}
            <span class="text-muted">— {{ component.detail }}</span>
          </li>
        </ul>
      </dd>
    </template>
    <dt class="col-sm-2">attributes</dt>
    <dd class="col-sm-10">
      {{ indicator.attribute_count }} ({{ indicator.ids_attribute_count }} for
      IDS) ·
      {{ indicator.categories.join(", ") || "no category" }}
    </dd>
    <dt class="col-sm-2">organisations</dt>
    <dd class="col-sm-10">
      <span
        v-for="org in indicator.organisations"
        :key="`${org.id}-${org.name}`"
        class="me-2"
        >{{ org.name }} ({{ org.event_count }})</span
      >
    </dd>
    <dt class="col-sm-2">sources</dt>
    <dd class="col-sm-10">
      <span
        v-for="source in indicator.sources"
        :key="`${source.type}-${source.id}-${source.name}`"
        class="me-2"
        >{{ sourceLabel(source) }} ({{ source.event_count }})</span
      >
    </dd>
    <dt class="col-sm-2">sightings</dt>
    <dd class="col-sm-10">
      <span class="text-success">+{{ indicator.sightings.positive }}</span>
      <span class="text-danger ms-2"
        >fp {{ indicator.sightings.false_positive }}</span
      >
      <span class="text-muted ms-2"
        >expired {{ indicator.sightings.expiration }}</span
      >
      <span v-if="indicator.sightings.last_at" class="text-muted ms-2"
        >· last <Timestamp :timestamp="indicator.sightings.last_at"
      /></span>
    </dd>
    <template v-if="indicator.warninglist_hits.length">
      <dt class="col-sm-2">warninglists</dt>
      <dd class="col-sm-10">
        <span
          v-for="hit in indicator.warninglist_hits"
          :key="hit"
          class="badge text-bg-warning me-1"
          >{{ hit }}</span
        >
      </dd>
    </template>
    <template v-if="(indicator.local_list_hits || []).length">
      <dt class="col-sm-2">organisation lists</dt>
      <dd class="col-sm-10">
        <template v-for="id in indicator.local_list_hits" :key="id">
          <RouterLink
            v-if="localLists[id]"
            :to="`/settings/warninglists/local/${id}`"
            class="badge text-bg-warning text-decoration-none me-1"
            @click.stop
            >{{ localLists[id].name }}</RouterLink
          >
          <span
            v-else
            class="badge text-bg-light border me-1"
            title="Another organisation's list: only they see it"
            >another organisation's list</span
          >
        </template>
      </dd>
    </template>
    <template v-if="(indicator.validation_issues || []).length">
      <dt class="col-sm-2">validation</dt>
      <dd class="col-sm-10">
        <span
          v-for="issue in indicator.validation_issues"
          :key="issue"
          class="badge text-bg-danger me-1"
          >{{ issue }}</span
        >
      </dd>
    </template>
    <template v-if="indicator.review">
      <dt class="col-sm-2">review</dt>
      <dd class="col-sm-10">
        {{ indicator.review.status }}
        <template v-if="indicator.review.until">
          until <Timestamp :timestamp="indicator.review.until" />
        </template>
        <span class="text-muted">
          · <Timestamp :timestamp="indicator.review.at"
        /></span>
      </dd>
    </template>
    <dt class="col-sm-2">tags</dt>
    <dd class="col-sm-10">
      <span
        v-for="tag in indicator.tags"
        :key="tag"
        class="badge text-bg-light border me-1 text-truncate mw-100"
        >{{ tag }}</span
      >
    </dd>
    <dt class="col-sm-2">events</dt>
    <dd class="col-sm-10">
      <RouterLink
        v-for="eventUuid in indicator.events"
        :key="eventUuid"
        :to="`/events/${eventUuid}`"
        class="font-monospace me-2"
        @click.stop
        >{{ eventUuid.slice(0, 8) }}</RouterLink
      >
      <span
        v-if="indicator.event_count > indicator.events.length"
        class="text-muted"
        >and {{ indicator.event_count - indicator.events.length }} more</span
      >
    </dd>
    <dt class="col-sm-2">uuid</dt>
    <dd class="col-sm-10 font-monospace">{{ indicator.uuid }}</dd>
  </dl>
</template>
