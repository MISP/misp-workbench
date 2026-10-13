<script setup>
// A feed's, MISP server's or organisation's trust in indicator scoring.
const props = defineProps({
  modifier: { type: Number, default: 0 },
  cap: { type: Number, default: null },
  idPrefix: { type: String, required: true },
});
const emit = defineEmits(["update:modifier", "update:cap"]);

function setModifier(event) {
  emit("update:modifier", Number(event.target.value) || 0);
}
function setCap(event) {
  // Empty means no cap.
  emit(
    "update:cap",
    event.target.value === "" ? null : Number(event.target.value),
  );
}
</script>

<template>
  <fieldset class="border rounded p-3 mb-3">
    <legend class="float-none w-auto px-2 fs-6 mb-0">Indicator scoring</legend>
    <div class="row g-3">
      <div class="col-md-6">
        <label class="form-label" :for="`${idPrefix}-score-modifier`"
          >Score modifier</label
        >
        <input
          :id="`${idPrefix}-score-modifier`"
          type="number"
          min="-100"
          max="100"
          class="form-control"
          :value="props.modifier ?? 0"
          @input="setModifier"
        />
        <div class="form-text">
          Points added to (or, negative, taken off) the confidence score of what
          this source reports.
        </div>
      </div>
      <div class="col-md-6">
        <label class="form-label" :for="`${idPrefix}-score-cap`"
          >Score cap</label
        >
        <input
          :id="`${idPrefix}-score-cap`"
          type="number"
          min="0"
          max="100"
          placeholder="none"
          class="form-control"
          :value="props.cap ?? ''"
          @input="setCap"
        />
        <div class="form-text">
          The highest score a value reported only by sources capped like this
          can reach. Empty for none.
        </div>
      </div>
    </div>
  </fieldset>
</template>
