<script setup>
import { storeToRefs } from "pinia";
import { useEventsStore } from "@/stores";
import { RouterLink } from "vue-router";
import Spinner from "@/components/Spinner.vue";
const eventsStore = useEventsStore();
const { events } = storeToRefs(eventsStore);
eventsStore.getAll();
</script>

<template>
    <Spinner v-if="events.loading" />
    <div v-if="events.error" class="text-danger">
        Error loading events: {{ events.error }}
    </div>
    <div class="table-responsive-sm">
        <table v-if="!events.loading" class="table table-striped">
            <thead>
                <tr>
                <th scope="col">id</th>
                <th scope="col">info</th>
                <th scope="col">date</th>
                <th scope="col" class="d-none d-sm-table-cell">distribution</th>
                <th scope="col">actions</th>
                </tr>
            </thead>
            <tbody>
                <tr :key="event.id" v-for="event in events">
                    <td>
                        <RouterLink :to="`/events/${event.id}`">{{ event.id }}</RouterLink>
                    </td>
                    <td>{{ event.info}}</td>
                    <td>{{ event.date}}</td>
                    <td class="d-none d-sm-table-cell">{{ event.distribution }}</td>
                    <td>
                        <div class="flex-wrap" :class="{ 'btn-group-vertical': $isMobile, 'btn-group': !$isMobile}" aria-label="Event Actions">
                            <RouterLink :to="`/events/delete/${event.id}`" tag="button" class="btn btn-danger">
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