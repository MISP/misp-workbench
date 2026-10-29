<script setup>
import { computed } from "vue";
import CollapsibleSection from "@/components/misc/CollapsibleSection.vue";
import SourceTrustFields from "@/components/indicators/SourceTrustFields.vue";
import { sourceTrustSummary } from "@/helpers/sourceTrust";

// SourceTrustFields under a collapsed "Advanced settings" section, for the
// MISP server and organisation forms (feeds add their authentication to
// theirs): most never change it, and the header shows when someone has.
const props = defineProps({
  modifier: { type: Number, default: 0 },
  cap: { type: Number, default: null },
  idPrefix: { type: String, required: true },
});
const emit = defineEmits(["update:modifier", "update:cap"]);

const summary = computed(
  () =>
    sourceTrustSummary(props.modifier, props.cap).join(" · ") ||
    "Indicator scoring: defaults",
);
</script>

<template>
  <CollapsibleSection title="Advanced settings" :summary="summary">
    <SourceTrustFields
      class="mb-0"
      :id-prefix="idPrefix"
      :modifier="modifier"
      :cap="cap"
      @update:modifier="emit('update:modifier', $event)"
      @update:cap="emit('update:cap', $event)"
    />
  </CollapsibleSection>
</template>
