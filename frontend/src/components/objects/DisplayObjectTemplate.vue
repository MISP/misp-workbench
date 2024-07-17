<script setup>
import { ref } from 'vue';


const props = defineProps(['template']);
const template = ref(props.template);

</script>

<template>
    <div class="mt-3">
        <span class="fw-bold">{{ template.name }} </span> ({{ template.uuid }})
        <span class="badge bg-secondary">{{ template.meta_category }}</span>
        <div>{{ template.description }}</div>
    </div>
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
                    <td>{{ attribute.name }} </td>
                    <td>{{ attribute.misp_attribute }}</td>
                    <td>{{ attribute.disable_correlation }}</td>
                    <td>{{ attribute.multiple }}</td>
                </tr>
                <tr>
                    <td></td>
                    <td colspan="3" class="text-secondary">{{ attribute.description }}</td>
                </tr>
            </template>
        </tbody>
    </table>
</template>