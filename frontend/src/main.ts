import { createApp } from "vue";
import { createPinia } from "pinia";

import App from "@/App.vue";
import { router } from "@/router";

import Popper from "vue3-popper";
import "bootstrap/dist/css/bootstrap.min.css";
import "bootstrap/dist/js/bootstrap.js"
import { library } from '@fortawesome/fontawesome-svg-core'
import { FontAwesomeIcon } from '@fortawesome/vue-fontawesome'
import { faPen, faEye, faTrash, faAngleUp, faAngleDoubleUp, faAngleDown, faAngleDoubleDown, faCopy, faBars, faEnvelopeOpenText, faBuilding, faUsers, faServer, faArrowRightFromBracket, faDownLong, faUpLong, faTags, faTag, faShapes, faCubesStacked, faArrowUp, faArrowDown, faCheck, faCheckDouble, faSync, faNetworkWired, faFileLines, faLink, faQuestion, faMoneyCheckDollar, faPerson, faSkullCrossbones, faCircleInfo, faCircle} from '@fortawesome/free-solid-svg-icons'
library.add(faPen, faEye, faTrash, faAngleUp, faAngleDoubleUp, faAngleDown, faAngleDoubleDown, faCopy, faBars, faEnvelopeOpenText, faBuilding, faUsers, faServer, faArrowRightFromBracket, faDownLong, faUpLong, faTags, faTag, faShapes, faCubesStacked, faArrowUp, faArrowDown, faCheck, faCheckDouble, faSync, faNetworkWired, faFileLines, faLink, faQuestion, faMoneyCheckDollar, faPerson, faSkullCrossbones, faCircleInfo);

const app = createApp(App);
app.component('font-awesome-icon', FontAwesomeIcon);
app.component("Popper", Popper);
app.config.globalProperties.$isMobile = window.innerWidth < 768;

app.use(createPinia());
app.use(router);

app.mount("#app");