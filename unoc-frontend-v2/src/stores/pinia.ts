import { createPinia } from 'pinia'

// Central, singleton Pinia instance shared across the root app and all cockpit sub-apps
export const pinia = createPinia()
