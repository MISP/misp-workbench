<script setup>
import { computed, watch, onMounted } from "vue";
import { storeToRefs } from "pinia";
import { useAuthStore, useAnalystDataStore } from "@/stores";
import { authHelper } from "@/helpers";
import OpinionScale from "@/components/analyst-data/OpinionScale.vue";
import Timestamp from "@/components/misc/Timestamp.vue";
import UUID from "@/components/misc/UUID.vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import {
  faNoteSticky,
  faCommentDots,
  faLink,
  faPen,
  faTrash,
  faReply,
} from "@fortawesome/free-solid-svg-icons";

// One node of an analyst data thread. Renders itself and then recurses into
// its own notes, opinions and relationships, which the API returns nested.
const props = defineProps({
  node: { type: Object, required: true },
  depth: { type: Number, default: 0 },
});

const emit = defineEmits(["reply", "edit", "delete"]);

const authStore = useAuthStore();
const { scopes, decoded_access_token } = storeToRefs(authStore);

const analystDataStore = useAnalystDataStore();
const { targets } = storeToRefs(analystDataStore);

const data = computed(() => props.node.data ?? {});

/**
 * Only the creating organisation may edit or delete analyst data, so the API
 * answers 403 for anyone else. The token carries the user's email rather than
 * their org uuid, so the buttons are shown to the author (and to an admin)
 * and hidden otherwise -- narrower than the API allows, but it never offers an
 * action that would be refused.
 */
const isOwn = computed(
  () =>
    authHelper.hasScope(scopes.value, "*") ||
    (Boolean(data.value.authors) &&
      data.value.authors === decoded_access_token.value?.sub),
);

const canUpdate = computed(
  () => isOwn.value && authHelper.hasScope(scopes.value, "analyst_data:update"),
);
const canDelete = computed(
  () => isOwn.value && authHelper.hasScope(scopes.value, "analyst_data:delete"),
);
// Replying creates new analyst data of the reader's own, so it is not gated on
// who wrote the note being replied to.
const canCreate = computed(() =>
  authHelper.hasScope(scopes.value, "analyst_data:create"),
);

const typeIcon = {
  Note: faNoteSticky,
  Opinion: faCommentDots,
  Relationship: faLink,
};

// Replies are indented, but only so far -- a deep thread should stay readable
// rather than walk off the right edge of the card.
const indent = computed(() => Math.min(props.depth, 4) * 1.5);

/**
 * What a relationship points at, resolved to a name and a link.
 *
 * The document stores only the uuid and the type, so the record is looked up.
 * The store caches by type and uuid, so several relationships pointing at the
 * same thing cost one request.
 */
const relatedTarget = computed(() => {
  void targets.value;
  if (props.node.analyst_type !== "Relationship") return null;
  return analystDataStore.targetFor(
    data.value.related_object_type,
    data.value.related_object_uuid,
  );
});

function resolveRelatedTarget() {
  if (props.node.analyst_type !== "Relationship") return;
  analystDataStore.resolveTarget(
    data.value.related_object_type,
    data.value.related_object_uuid,
  );
}

onMounted(resolveRelatedTarget);
watch(() => data.value.related_object_uuid, resolveRelatedTarget);

const children = computed(() => [
  ...(props.node.notes ?? []),
  ...(props.node.opinions ?? []),
  ...(props.node.relationships ?? []),
]);
</script>

<template>
  <div class="analyst-node" :style="{ marginLeft: `${indent}rem` }">
    <div class="border-start border-2 ps-3 py-2">
      <div class="d-flex align-items-start gap-2">
        <FontAwesomeIcon
          :icon="typeIcon[node.analyst_type]"
          class="text-body-secondary mt-1"
          :title="node.analyst_type"
        />

        <div class="flex-grow-1">
          <!-- Note -->
          <div v-if="node.analyst_type === 'Note'">
            <div class="analyst-text">{{ data.note }}</div>
            <span
              v-if="data.language"
              class="badge text-bg-light border ms-0 mt-1"
            >
              {{ data.language }}
            </span>
          </div>

          <!-- Opinion -->
          <div v-else-if="node.analyst_type === 'Opinion'">
            <OpinionScale :opinion="data.opinion ?? 0" />
            <div class="analyst-text mt-1">{{ data.comment }}</div>
          </div>

          <!-- Relationship -->
          <div v-else-if="node.analyst_type === 'Relationship'">
            <span class="badge text-bg-primary">
              {{ data.relationship_type }}
            </span>
            <span class="badge text-bg-secondary ms-1">
              {{ data.related_object_type }}
            </span>

            <div class="mt-1">
              <!-- named and linked once resolved -->
              <RouterLink
                v-if="relatedTarget?.route"
                :to="relatedTarget.route"
                class="analyst-target"
              >
                {{ relatedTarget.label }}
              </RouterLink>
              <span
                v-else-if="relatedTarget?.missing"
                class="text-body-secondary fst-italic"
              >
                no longer available
              </span>
              <span v-else-if="relatedTarget" class="analyst-target">
                {{ relatedTarget.label ?? data.related_object_uuid }}
              </span>
              <span v-else class="placeholder-glow">
                <span class="placeholder" style="width: 8rem"></span>
              </span>

              <div
                v-if="relatedTarget?.sublabel"
                class="text-body-secondary small"
              >
                {{ relatedTarget.sublabel }}
              </div>

              <div v-if="data.related_object_uuid" class="mt-1">
                <UUID :uuid="data.related_object_uuid" />
              </div>
            </div>
          </div>

          <div class="text-body-secondary small mt-1">
            <span v-if="data.authors">{{ data.authors }}</span>
            <span v-if="data.created" class="ms-2">
              <Timestamp :timestamp="data.created" />
            </span>
          </div>
        </div>

        <div class="btn-group btn-group-sm" role="group">
          <button
            v-if="canCreate"
            type="button"
            class="btn btn-outline-secondary"
            title="Reply to this"
            @click="emit('reply', node)"
          >
            <FontAwesomeIcon :icon="faReply" />
          </button>
          <button
            v-if="canUpdate"
            type="button"
            class="btn btn-outline-primary"
            title="Edit"
            @click="emit('edit', node)"
          >
            <FontAwesomeIcon :icon="faPen" />
          </button>
          <button
            v-if="canDelete"
            type="button"
            class="btn btn-outline-danger"
            title="Delete"
            @click="emit('delete', node)"
          >
            <FontAwesomeIcon :icon="faTrash" />
          </button>
        </div>
      </div>

      <!-- replies, same shape as their parent -->
      <AnalystDataNode
        v-for="child in children"
        :key="child.uuid"
        :node="child"
        :depth="depth + 1"
        @reply="emit('reply', $event)"
        @edit="emit('edit', $event)"
        @delete="emit('delete', $event)"
      />
    </div>
  </div>
</template>

<style scoped>
.analyst-target {
  word-break: break-all;
}

.analyst-text {
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
