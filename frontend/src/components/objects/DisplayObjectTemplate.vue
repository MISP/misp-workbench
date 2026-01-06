<script setup>
import { ref } from "vue";
import UUID from "@/components/misc/UUID.vue";

const props = defineProps(["template"]);
const template = ref(props.template);
</script>

<template>
  <div class="mt-3">
    <span class="fw-bold">{{ template.name }} </span>
    <UUID :uuid="template.uuid" />
    <span class="badge bg-secondary">{{ template.meta_category }}</span>
    <div>{{ template.description }}</div>
  </div>
  <p>
    <a
      class="btn-primary"
      data-bs-toggle="collapse"
      href="#templateDetails"
      role="button"
      aria-expanded="false"
      aria-controls="advancedSettings"
    >
      <button type="button" class="btn btn-outline-secondary">
        Template details <font-awesome-icon icon="fa-solid fa-caret-down" />
      </button>
    </a>
  </p>
  <div class="collapse" id="templateDetails">
    <table class="table">
      <thead>
        <tr>
          <th style="width: 30%" scope="col">type</th>
          <th style="width: 30%" scope="col">MISP type</th>
          <th style="width: 30%" scope="col">correlate</th>
          <th style="width: 30%" scope="col">multiple</th>
        </tr>
      </thead>
      <tbody>
        <template :key="attribute.id" v-for="attribute in template.attributes">
          <tr>
            <td>{{ attribute.name }}</td>
            <td>{{ attribute.misp_attribute }}</td>
            <td>{{ attribute.disable_correlation }}</td>
            <td>{{ attribute.multiple }}</td>
          </tr>
          <tr>
            <td></td>
            <td colspan="3" class="text-secondary">
              {{ attribute.description }}
            </td>
          </tr>
        </template>
      </tbody>
    </table>
  </div>
</template>
