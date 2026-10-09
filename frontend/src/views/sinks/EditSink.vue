<script setup>
import { storeToRefs } from "pinia";
import { useSinksStore } from "@/stores";
import SinkForm from "@/components/sinks/SinkForm.vue";
import Spinner from "@/components/misc/Spinner.vue";

const props = defineProps(["id"]);
const sinksStore = useSinksStore();
const { sink, status } = storeToRefs(sinksStore);
sink.value = null;
sinksStore.getById(props.id);
</script>

<template>
  <Spinner v-if="status.loading || !sink" />
  <!-- keyed so the form re-initialises when another sink is opened -->
  <SinkForm v-else :key="sink.id" :sink="sink" />
</template>
