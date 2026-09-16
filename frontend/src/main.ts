// Our stylesheet first: it declares the cascade layer order before Vuetify's CSS loads.
import './styles/main.css'
import 'vuetify/styles'

import { createApp } from 'vue'
import App from './App.vue'
import { router } from './router'
import { vuetify } from './plugins/vuetify'

createApp(App).use(vuetify).use(router).mount('#app')
