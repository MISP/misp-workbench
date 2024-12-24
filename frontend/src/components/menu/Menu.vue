<script>
import { useAuthStore } from "@/stores";

export default {
    data() {
        return {
            visible: false,
            authStore: useAuthStore()
        }
    }
};

</script>

<style>
.mobile-menu-item {
    font-size: xx-large;
    line-height: 0;
    width: 5rem;
}
</style>

<template>
    <nav v-if="!$isMobile" class="navbar navbar-expand navbar-dark bg-dark">
        <div class="container-fluid">
            <div class="navbar-nav collapse navbar-collapse">
                <RouterLink to="/" class="nav-item nav-link">
                    <img src="/images/misp-logo-pixel.png" alt="" height="30">
                </RouterLink>
                <RouterLink to="/events" class="nav-item nav-link">events</RouterLink>
                <RouterLink to="/organisations" class="nav-item nav-link">organisations</RouterLink>
                <RouterLink to="/users" class="nav-item nav-link">users</RouterLink>
                <RouterLink to="/servers" class="nav-item nav-link">servers</RouterLink>
                <RouterLink to="/feeds" class="nav-item nav-link">feeds</RouterLink>
                <div class="nav-item dropdown navbar-dark bg-dark">
                    <a class="nav-link dropdown-toggle" href="#" id="navbarScrollingDropdown" role="button"
                        data-bs-toggle="dropdown" aria-expanded="false">
                        settings
                    </a>
                    <ul class="dropdown-menu" aria-labelledby="navbarScrollingDropdown">
                        <li>
                            <RouterLink to="/settings/modules" class="dropdown-item">modules</RouterLink>
                        </li>
                        <hr class="dropdown-divider">
                        <li>
                            <RouterLink to="/settings/taxonomies" class="dropdown-item">taxonomies</RouterLink>
                        </li>
                        <li>
                            <RouterLink to="/settings/galaxies" class="dropdown-item">galaxies</RouterLink>
                        </li>
                        <hr class="dropdown-divider">
                        <li>
                            <RouterLink to="/settings/internals" class="dropdown-item">internals</RouterLink>
                        </li>
                    </ul>
                </div>
            </div>
            <form class="d-flex">
                <button @click="authStore.logout()" class="btn btn-sm btn-outline-secondary"
                    type="button">logout</button>
            </form>
        </div>
    </nav>
    <div v-if="$isMobile" class="sticky-top">
        <div class="bg-dark">
            <a class="mobile-menu-item nav-pills nav-item nav-link d-block p-3 link-dark text-center border-end border-secondary"
                data-bs-toggle="collapse" href="#collapsable-menu" role="button" aria-expanded="false"
                aria-controls="collapsable-menu" @click="visible = !visible">
                <font-awesome-icon icon="fa-solid fa-bars" inverse />
            </a>
        </div>
        <div class="position-absolute d-flex flex-column flex-shrink-0 bg-dark">
            <div id="collapsable-menu" :class="visible ? null : 'collapse'">
                <ul class="nav nav-pills nav-flush flex-column mb-auto text-center">
                    <li class="nav-item mobile-menu-item">
                        <RouterLink @click="visible = !visible" to="/events"
                            class="nav-item nav-link py-3 border-bottom" aria-current="page" title="">
                            <font-awesome-icon icon="fa-solid fa-envelope-open-text" inverse />
                        </RouterLink>
                    </li>
                    <li class="nav-item mobile-menu-item">
                        <RouterLink @click="visible = !visible" to="/organisations"
                            class="nav-item nav-link mobile-menu-item nav-link py-3 border-bottom" title="">
                            <font-awesome-icon icon="fa-ssolid fa-building" inverse />
                        </RouterLink>
                    </li>
                    <li class="nav-item mobile-menu-item">
                        <RouterLink @click="visible = !visible" to="/users" class="nav-item nav-link py-3 border-bottom"
                            title="">
                            <font-awesome-icon icon="fa-ssolid fa-users" inverse />
                        </RouterLink>
                    </li>
                    <li class="nav-item mobile-menu-item">
                        <RouterLink @click="visible = !visible" to="/servers"
                            class="nav-item nav-link py-3 border-bottom" title="">
                            <font-awesome-icon icon="fa-ssolid fa-server" inverse />
                        </RouterLink>
                    </li>
                    <li class="nav-item mobile-menu-item">
                        <a @click="authStore.logout()" class="nav-item nav-link py-3 border-bottom" title="">
                            <font-awesome-icon icon="fa-ssolid fa-arrow-right-from-bracket" inverse />
                        </a>
                    </li>
                </ul>
            </div>
        </div>
    </div>
</template>