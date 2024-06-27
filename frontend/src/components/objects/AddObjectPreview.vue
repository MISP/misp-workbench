<script setup>

const props = defineProps(['object', 'template']);

</script>

<template>
    <div class="mt-3">
        <span class="fw-bold">{{ template.name }} </span> ({{ template.uuid }})
    </div>
    <div class="container mt-3">
        <div class="table-responsive">
            <table class="table table-bordered table-striped table-hover">
                <thead class="">
                    <tr>
                        <th scope="col">value</th>
                        <th scope="col">type</th>
                        <th scope="col">to_ids</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="attribute in object.attributes">
                        <td>{{ attribute.value }}</td>
                        <td>{{ attribute.type }}</td>
                        <td>{{ attribute.to_ids }}</td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>
</template>