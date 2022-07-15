<script setup>
  defineProps(['event'])
</script>

<style>
.single-stat-card .card-body {
    font-size: x-large;
    text-align: center;
    padding: 0;
}
.single-stat-card .card-body p {
    margin-bottom: 0;
}
</style>
<template>
    <div class="card shadow-sm">
        <div class="event-title card-header border-bottom border-gray-300">
            <div class="row">
                <div class="col-10">
                    <h2 class="h3"><span class="badge bg-danger mx-1">tlp:red</span>ThinkPHP Remote Code Execution Vulnerability</h2>
                </div>
                <div class="col-2">
                    <div class="flex-wrap" :class="{ 'btn-group-vertical': $isMobile, 'btn-group': !$isMobile}" aria-label="Event Actions">
                        <RouterLink :to="`/events/delete/${event.id}`" tag="button" class="btn btn-danger">
                            <font-awesome-icon icon="fa-solid fa-trash" />
                        </RouterLink>
                        <RouterLink :to="`/events/update/${event.id}`" tag="button" class="btn btn-primary">
                            <font-awesome-icon icon="fa-solid fa-pen" />
                        </RouterLink>
                    </div>
                </div>
            </div>
        </div>
        <div class="row m-1">
            <div class="col-sm-6 mt-2">
                <div class="card rounded border border-gray-300 shadow h-100">
                    <div class="card-header">general</div>
                    <div class="card-body d-flex flex-column">
                        <div class="table-responsive-sm">
                            <table class="table table-striped">
                                <tbody>
                                    <tr>
                                        <th scope="row">id</th>
                                        <td>{{ event.id }}</td>
                                    </tr>
                                    <tr>
                                        <th scope="row">uuid</th>
                                        <td>{{ event.uuid }} <font-awesome-icon class="text-primary" icon="fa-solid fa-copy" /></td>
                                    </tr>
                                    <tr>
                                        <th scope="row">published</th>
                                        <td>{{ event.published }}</td>
                                    </tr>
                                    <tr>
                                        <th scope="row">creator user</th>
                                        <td>{{ event.user_id }}</td>
                                    </tr>
                                    <tr>
                                        <th scope="row">protected</th>
                                        <td></td>
                                    </tr>
                                    <tr>
                                        <th scope="row">date</th>
                                        <td>{{ event.date }}</td>
                                    </tr>
                                    <tr>
                                        <th scope="row">threat level</th>
                                        <td>{{ event.threat_level_id }}</td>
                                    </tr>
                                    <tr>
                                        <th scope="row">analysis</th>
                                        <td>{{ event.analysis }}</td>
                                    </tr>
                                    <tr>
                                        <th scope="row">distribution</th>
                                        <td>{{ event.distribution }}</td>
                                    </tr>
                                    <tr>
                                        <th scope="row">attributes</th>
                                        <td>{{ event.attribute_count }} (0 objects)</td>
                                    </tr>
                                    <tr>
                                        <th scope="row">correlation</th>
                                        <td>{{ !event.disable_correlation }}</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
            <div class="col">
                <div class="mt-2">
                    <div class="card rounded border border-gray-300 shadow">
                        <div class="card-header">stats</div>
                        <div class="card-body d-flex flex-column">
                            <div class="card-text">
                                <img src="/public/images/pie-chart.png" class="card-img">
                            </div>
                        </div>
                    </div>
                </div>
                <div class="mt-2">
                    <div class="card rounded border border-gray-300 shadow">
                        <div class="card-header">tags</div>
                        <div class="card-body d-flex flex-column">
                            <div class="card-text">
                                <div class="col-auto">
                                <span class="badge bg-danger mx-1">tlp:red</span>
                                    <span class="badge bg-warning mx-1">phishing</span>
                                    <span class="badge bg-info mx-1">malware</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="col col-sm-2">
                <div class="mt-2">
                    <div class="card">
                        <div class="card-body">
                            <div class="d-flex justify-content-between align-items-center">
                                <div>
                                    <p class="mb-0 text-muted">correlations</p>
                                    <h2>8,523</h2>
                                </div>
                                <span class="badge badge-pill badge-cyan badge-red bg-warning">
                                    <font-awesome-icon icon="fa-solid fa-down-long" />
                                    <span class="font-weight-semibold ml-1">6.71%</span>
                                </span>
                            </div>

                        </div>
                        <div class="card-footer text-muted">
                            <p class="card-text fst-italic fw-light"><small class="text-muted ">last day/<span class="fw-bold text-decoration-underline">week</span>/month</small></p>
                        </div>
                    </div>
                </div>
                <div class="mt-2">
                    <div class="card">
                        <div class="card-body">
                            <div class="d-flex justify-content-between align-items-center">
                                <div>
                                    <p class="mb-0 text-muted">sightings</p>
                                    <h2>423</h2>
                                </div>
                                <span class="badge badge-pill badge-cyan badge-red bg-danger">
                                    <font-awesome-icon icon="fa-solid fa-up-long" />
                                    <span class="font-weight-semibold ml-1">16.71%</span>
                                </span>
                            </div>
                        </div>
                        <div class="card-footer text-muted">
                            <p class="card-text fst-italic fw-light"><small class="text-muted">last day/week/<span class="fw-bold text-decoration-underline">month</span></small></p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        <div class="row m-1">
            <div class="col-sm-3 mt-2">
                <div class="card rounded border border-gray-300 shadow">
                <div class="card-header">organisation</div>
                    <div class="card-body d-flex flex-column">
                        <div class="card-text">
                            <div class="row">
                                <div class="col"><img src="/public/images/CIRCL.png" alt="" height="30"></div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        <div class="card-footer text-muted">
            <p class="card-text"><small class="text-muted">last updated 3 mins ago by <a href="/users/123">adulau</a></small></p>
        </div>
    </div>
</template>