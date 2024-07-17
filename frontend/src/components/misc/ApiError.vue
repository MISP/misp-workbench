<script setup>

const props = defineProps(['errors']);
console.log(props.errors);
</script>

<template>
    <div v-if="Array.isArray(errors)">
        <ul>
            <li v-for="error in errors">
                <span class="fw-bold">{{ error.loc[1] }}:</span> {{ error.msg }}
            </li>
        </ul>
    </div>
    <p>
        {{ errors }}
    </p>
</template>