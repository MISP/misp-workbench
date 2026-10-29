<script setup>
import { ref, onMounted } from "vue";
import Badge from "@/components/misc/Badge.vue";
import Timestamp from "@/components/misc/Timestamp.vue";
import DistributionLevel from "@/components/enums/DistributionLevel.vue";
import { useAttributesStore } from "@/stores";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faShield } from "@fortawesome/free-solid-svg-icons";

// An event's metadata and its first attributes, loaded when its Explore card
// opens.
const props = defineProps({ event: { type: Object, required: true } });

const ATTRIBUTES = 10;
const attributesStore = useAttributesStore();

const attributes = ref([]);
const total = ref(0);
const loading = ref(true);
const error = ref(null);

function sourceLabel(source) {
  if (!source) return null;
  return source.type === "feed" || source.type === "server"
    ? `${source.type}: ${source.name}`
    : source.type;
}

onMounted(async () => {
  try {
    const response = await attributesStore.searchLookup({
      query: `event_uuid:"${props.event.uuid}"`,
      page: 1,
      size: ATTRIBUTES,
    });
    attributes.value = response.results.map((hit) => hit._source);
    // The event's own count is exact; a search's total can stop at 10,000.
    total.value = props.event.attribute_count ?? response.total;
  } catch (e) {
    error.value = e;
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <div class="small">
    <dl class="row mb-0 mx-0">
      <dt class="col-sm-2">date</dt>
      <dd class="col-sm-10">{{ event.date }}</dd>
      <template v-if="sourceLabel(event.source)">
        <dt class="col-sm-2">source</dt>
        <dd class="col-sm-10">{{ sourceLabel(event.source) }}</dd>
      </template>
      <dt class="col-sm-2">distribution</dt>
      <dd class="col-sm-10">
        <DistributionLevel :distribution_level_id="event.distribution" />
        <span v-if="event.sharing_group?.name">
          ({{ event.sharing_group.name }})</span
        >
      </dd>
      <dt class="col-sm-2">published</dt>
      <dd class="col-sm-10">
        <template v-if="event.published">
          <Timestamp :timestamp="event.publish_timestamp" />
        </template>
        <template v-else>no</template>
      </dd>
      <template v-if="event.extends_uuid">
        <dt class="col-sm-2">extends</dt>
        <dd class="col-sm-10">
          <RouterLink
            :to="`/events/${event.extends_uuid}`"
            class="font-monospace"
            >{{ event.extends_uuid }}</RouterLink
          >
        </dd>
      </template>
    </dl>

    <h6 class="mt-3">
      Attributes
      <span v-if="!loading" class="text-muted fw-normal">({{ total }})</span>
    </h6>
    <div v-if="loading" class="text-muted">Loading…</div>
    <div v-else-if="error" class="text-danger">{{ error }}</div>
    <p v-else-if="!attributes.length" class="text-muted mb-0">None.</p>
    <template v-else>
      <table class="table table-sm mb-1">
        <tbody>
          <tr v-for="attribute in attributes" :key="attribute.uuid">
            <td class="text-nowrap"><Badge :value="attribute.type" /></td>
            <td class="font-monospace text-break w-100">
              {{ attribute.value }}
            </td>
            <td class="text-muted text-nowrap">{{ attribute.category }}</td>
            <td class="text-nowrap">
              <FontAwesomeIcon
                v-if="attribute.to_ids"
                :icon="faShield"
                class="text-danger"
                title="IDS"
              />
            </td>
          </tr>
        </tbody>
      </table>
      <RouterLink
        v-if="total > attributes.length"
        :to="`/events/${event.uuid}/attributes`"
      >
        All {{ total }} attributes
      </RouterLink>
    </template>
  </div>
</template>
