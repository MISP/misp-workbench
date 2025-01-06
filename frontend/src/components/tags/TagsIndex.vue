<script setup>
import { ref, computed } from 'vue';
import Badge from "@/components/misc/Badge.vue";
import { useTaxonomiesStore } from "@/stores";
import { storeToRefs } from 'pinia'
import { tagHelper } from "@/helpers";
import VueMultiselect from 'vue-multiselect'

const taxonomiesStore = useTaxonomiesStore();
const { taxonomies, status } = storeToRefs(taxonomiesStore);

defineProps({
  tags: {
    type: Array,
    required: true,
    default: () => [],
  }
});

const options = ref(["foo", "bar", "baz"])
const selected = ref([]);

taxonomiesStore.get({
  page: 1,
  size: 100, // FIXME: this is a hack, we should get all the taxonomies
  enabled: true,
});

const tags = computed(() => {
  let tags = [];

  if (!taxonomies.value.items) {
    return tags;
  }

  taxonomies.value.items.map((taxonomy) => {
    taxonomy.predicates.map((predicate) => {
      tags.push({
        name: tagHelper.getTag(taxonomy.namespace, predicate.value),
        colour: predicate.colour,
      });
    });
  });

  return tags;
});

</script>

<style scoped>
.tag {
  float: left;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin: 0.1em;
}
</style>
<template>
  <div>
    <VueMultiselect v-model="selected" :options="tags" :multiple="true" :close-on-select="true" label="name" track-by="name" placeholder="Select tag">
    </VueMultiselect>
  </div>

  <div class="col-auto">
    <Badge v-for="tag in tags" :key="tag.name" :value="tag.name" :colour="tag.colour" />
  </div>
</template>

<script>
export default {
  props: {
    tags: {
      type: Array,
      required: true,
    },
  }
};
</script>

<style scoped>
.badge {
  padding: 0.5em 1em;
}
</style>