<script setup>
import { storeToRefs } from "pinia";
import { useEventsStore } from "@/stores";
import { RouterLink } from "vue-router";
import Spinner from "@/components/misc/Spinner.vue";
import DistributionLevel from "@/components/enums/DistributionLevel.vue";
const eventsStore = useEventsStore();
const { events, status } = storeToRefs(eventsStore);
eventsStore.getAll();
</script>

<template>
    <Spinner v-if="status.loading" />
    <div v-if="status.error" class="text-danger">
        Error loading events: {{ status.error }}
    </div>
    <div class="table-responsive-sm">
        <table v-if="!status.loading" class="table table-striped">
            <thead>
                <tr>
                    <th scope="col">id</th>
                    <th scope="col">info</th>
                    <th scope="col">date</th>
                    <th scope="col" class="d-none d-sm-table-cell">distribution</th>
                    <th scope="col" class="text-end">actions</th>
                </tr>
            </thead>
            <tbody>
                <tr :key="event.id" v-for="event in events">
                    <td>
                        <RouterLink :to="`/events/${event.id}`">{{ event.id }}</RouterLink>
                    </td>
                    <td class="text-start">{{ event.info }}</td>
                    <td>{{ event.date }}</td>
                    <td class="d-none d-sm-table-cell">
                        <DistributionLevel :distribution_level_id=event.distribution />
                    </td>
                    <td class="text-end">
                        <div class="flex-wrap" :class="{ 'btn-group-vertical': $isMobile, 'btn-group': !$isMobile }"
                            aria-label="Event Actions">
                            <RouterLink :to="`/events/delete/${event.id}`" tag="button" class="btn btn-danger disabled">
                                <font-awesome-icon icon="fa-solid fa-trash" />
                            </RouterLink>
                            <RouterLink :to="`/events/update/${event.id}`" tag="button" class="btn btn-primary">
                                <font-awesome-icon icon="fa-solid fa-pen" />
                            </RouterLink>
                            <RouterLink :to="`/events/${event.id}`" tag="button" class="btn btn-primary">
                                <font-awesome-icon icon="fa-solid fa-eye" />
                            </RouterLink>
                        </div>
                    </td>
                </tr>
            </tbody>
        </table>
    </div>
</template>