<script setup>

const props = defineProps(['errors']);

</script>

<template>

<ul>
    <li v-for="error in errors">
        <span class="fw-bold">{{ error.loc[1] }}:</span> {{ error.msg }}
    </li>
</ul>
</template>