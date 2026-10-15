<script setup>
import { computed } from "vue";
import { useRoute } from "vue-router";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faLock } from "@fortawesome/free-solid-svg-icons";
import { guardFor } from "@/components/menu/menu";

// Where the router guard sends a page the user's role doesn't open.
const route = useRoute();
const entry = computed(() =>
  typeof route.query.from === "string" ? guardFor(route.query.from) : null,
);
</script>

<template>
  <div class="card mx-auto mt-4" style="max-width: 560px">
    <div class="card-body text-center p-4">
      <FontAwesomeIcon
        :icon="faLock"
        size="2x"
        class="text-body-secondary mb-3"
      />
      <h4 class="mb-2">
        {{ entry ? `No access to ${entry.label}` : "No access to this page" }}
      </h4>
      <p class="text-body-secondary mb-4">
        <template v-if="entry">
          It needs the <code>{{ entry.scope }}</code> scope, which your role
          doesn't grant. Ask an administrator if you need it.
        </template>
        <template v-else>
          Your role doesn't grant what this page needs. Ask an administrator if
          you need it.
        </template>
      </p>
      <RouterLink to="/" class="btn btn-outline-primary">Go home</RouterLink>
    </div>
  </div>
</template>
