<script setup>
import CodeMirror from "vue-codemirror6";
import { basicSetup } from "codemirror";
import { json, jsonParseLinter } from "@codemirror/lang-json";

const modelValue = defineModel();
</script>

<template>
  <code-mirror
    v-model="modelValue"
    class="editor-container"
    :lang="json()"
    :linter="jsonParseLinter()"
    :extensions="[basicSetup]"
    :tab="true"
    :tab-size="4"
  />
</template>
