<script setup>
import { computed } from "vue";
import DOMPurify from "dompurify";

const props = defineProps({
  outputs: { type: Array, default: () => [] },
});

const items = computed(() => props.outputs || []);

function pickRichMime(data) {
  if (!data) return null;
  // Priority — richest first.
  for (const mime of [
    "text/html",
    "image/svg+xml",
    "image/png",
    "image/jpeg",
    "application/json",
    "text/plain",
  ]) {
    if (mime in data) return mime;
  }
  return null;
}

function safeHtml(html) {
  return DOMPurify.sanitize(String(html || ""));
}

function tracebackText(item) {
  if (Array.isArray(item.traceback)) return item.traceback.join("\n");
  return `${item.ename || "Error"}: ${item.evalue || ""}`;
}

function jsonPretty(value) {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}
</script>

<template>
  <div class="cell-output">
    <div v-if="items.length === 0" class="cell-output-empty"></div>
    <template v-for="(item, idx) in items" :key="idx">
      <pre
        v-if="item.output_type === 'stream'"
        class="cell-output-stream"
        :class="item.name === 'stderr' ? 'is-stderr' : ''"
        >{{ item.text }}</pre
      >

      <pre v-else-if="item.output_type === 'error'" class="cell-output-error">{{
        tracebackText(item)
      }}</pre>

      <template
        v-else-if="
          item.output_type === 'execute_result' ||
          item.output_type === 'display_data'
        "
      >
        <template v-if="pickRichMime(item.data) === 'text/html'">
          <div
            class="cell-output-html"
            v-html="safeHtml(item.data['text/html'])"
          ></div>
        </template>
        <template v-else-if="pickRichMime(item.data) === 'image/svg+xml'">
          <div
            class="cell-output-svg"
            v-html="safeHtml(item.data['image/svg+xml'])"
          ></div>
        </template>
        <template v-else-if="pickRichMime(item.data) === 'image/png'">
          <img
            class="cell-output-image"
            :src="`data:image/png;base64,${item.data['image/png']}`"
          />
        </template>
        <template v-else-if="pickRichMime(item.data) === 'image/jpeg'">
          <img
            class="cell-output-image"
            :src="`data:image/jpeg;base64,${item.data['image/jpeg']}`"
          />
        </template>
        <template v-else-if="pickRichMime(item.data) === 'application/json'">
          <pre class="cell-output-stream">{{
            jsonPretty(item.data["application/json"])
          }}</pre>
        </template>
        <template v-else>
          <pre class="cell-output-stream">{{
            item.data && item.data["text/plain"]
          }}</pre>
        </template>
      </template>

      <pre v-else class="cell-output-stream">{{ jsonPretty(item) }}</pre>
    </template>
  </div>
</template>

<style scoped>
.cell-output {
  padding: 6px 12px 10px 12px;
  background: var(--bs-tertiary-bg, #f8f9fa);
  border-left: 3px solid var(--bs-secondary-bg, #e9ecef);
  font-size: 0.875rem;
}
.cell-output-stream {
  margin: 0;
  padding: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-family:
    ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono",
    "Courier New", monospace;
  font-size: 0.8125rem;
}
.cell-output-stream.is-stderr {
  color: var(--bs-danger, #dc3545);
}
.cell-output-error {
  margin: 0;
  padding: 0;
  white-space: pre-wrap;
  word-break: break-word;
  color: var(--bs-danger, #dc3545);
  font-family:
    ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono",
    "Courier New", monospace;
  font-size: 0.8125rem;
}
.cell-output-image {
  max-width: 100%;
  height: auto;
}
.cell-output-html :deep(table) {
  font-size: 0.8125rem;
}
</style>
