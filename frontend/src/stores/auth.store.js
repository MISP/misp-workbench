import { defineStore } from 'pinia';

import { fetchWrapper } from '@/helpers';
import { router } from "@/router";

export const useAuthStore = defineStore({
    id: 'auth',
    state: () => ({
        // initialize state from local storage to enable user to stay logged in
        access_token: JSON.parse(localStorage.getItem('access_token')),
        returnUrl: null
    }),
    actions: {
        async authenticate(username, password) {
            const response = await fetchWrapper.authenticate(username, password);

            // update pinia state
            this.access_token = response.access_token;

            // store user details and jwt in local storage to keep user logged in between page refreshes
            localStorage.setItem('access_token', JSON.stringify(response.access_token));

            // redirect to previous url or default to home page
            router.push('/');
        },
        logout() {
            this.user = null;
            localStorage.removeItem('access_token');
            router.push('/login');
        }
    }
});