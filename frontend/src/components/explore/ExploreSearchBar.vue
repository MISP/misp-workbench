<script setup>
import { ref, onMounted, onUnmounted, watch } from "vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import {
  faFileLines,
  faFloppyDisk,
  faMagnifyingGlass,
} from "@fortawesome/free-solid-svg-icons";
import LuceneQuerySyntaxCheatsheet from "./LuceneQuerySyntaxCheatsheetModal.vue";

const props = defineProps({
  modelValue: { type: String, default: "" },
  storedSearches: { type: Array, default: () => [] },
});

const emit = defineEmits(["update:modelValue", "search", "save"]);

const isFocused = ref(false);
const animatedPlaceholder = ref("Search something (Lucene Query Syntax) ...");

const _examples = [
  "info:banking",
  "type.keyword:ip*",
  'expanded.ip2geo.country_iso_code:"RU"',
  "@timestamp:[2026-01-01 TO *]",
  '"admin@example.com"',
  'tags.name.keyword:"tlp:amber"',
  'uuid:"094cecb9-2bd0-4c15-97f1-21373601b36"',
];

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

let _stopAnim = false;
async function _runAnimatedPlaceholder() {
  const typingDelay = 40;
  const pauseDelay = 2000;
  while (!_stopAnim) {
    if (isFocused.value || props.modelValue?.length > 0) {
      animatedPlaceholder.value = "Search something (Lucene Query Syntax) ...";
      await sleep(300);
      continue;
    }
    for (let i = 0; i < _examples.length && !_stopAnim; i++) {
      const s = _examples[i];
      for (let j = 1; j <= s.length && !_stopAnim; j++) {
        if (isFocused.value || props.modelValue?.length > 0) break;
        animatedPlaceholder.value = s.slice(0, j);
        await sleep(typingDelay);
      }
      if (isFocused.value || props.modelValue?.length > 0) break;
      await sleep(pauseDelay);
      for (let j = s.length; j >= 0 && !_stopAnim; j--) {
        if (isFocused.value || props.modelValue?.length > 0) break;
        animatedPlaceholder.value = s.slice(0, j);
        await sleep(typingDelay / 2);
      }
      if (isFocused.value || props.modelValue?.length > 0) break;
      await sleep(200);
    }
  }
}

onMounted(() => {
  _stopAnim = false;
  _runAnimatedPlaceholder();
});

onUnmounted(() => {
  _stopAnim = true;
});

watch(
  () => props.modelValue,
  (v) => {
    if (v?.length > 0) animatedPlaceholder.value = "";
  },
);
</script>

<template>
  <div class="w-100">
    <div class="input-group mb-1">
      <button
        class="btn btn-outline-secondary"
        type="button"
        @click="emit('save', modelValue)"
      >
        <FontAwesomeIcon :icon="faFloppyDisk" />
      </button>
      <input
        type="text"
        class="form-control text-console"
        list="previous-searches"
        :placeholder="animatedPlaceholder"
        :value="modelValue"
        @input="emit('update:modelValue', $event.target.value)"
        @focus="isFocused = true"
        @blur="isFocused = false"
        @keyup.enter="emit('search')"
      />
      <datalist id="previous-searches">
        <option v-for="term in storedSearches" :key="term">{{ term }}</option>
      </datalist>
      <button class="btn btn-primary" type="button" @click="emit('search')">
        <FontAwesomeIcon :icon="faMagnifyingGlass" />
      </button>
    </div>
    <span class="text-muted fst-italic small d-flex align-items-center">
      Lucene query syntax supported
      <button
        type="button"
        class="btn btn-sm d-flex align-items-center"
        data-bs-toggle="modal"
        data-bs-target="#luceneQuerySyntaxCheatsheetModal"
      >
        <FontAwesomeIcon :icon="faFileLines" class="ms-1 cursor-pointer" />
      </button>
    </span>
    <LuceneQuerySyntaxCheatsheet />
  </div>
</template>
