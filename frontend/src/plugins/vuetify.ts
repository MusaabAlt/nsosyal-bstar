import { createVuetify } from 'vuetify'
import { aliases, mdi } from 'vuetify/iconsets/mdi-svg'

/*
 * Vuetify supplies the application root; every visual decision comes from
 * src/styles/tokens.css (the ATI-SOSYAL Paneli design). Ripples and
 * elevation are switched off so nothing Material leaks into the panel.
 */
export const vuetify = createVuetify({
  theme: {
    defaultTheme: 'nsosyal',
    variations: false,
    themes: {
      nsosyal: {
        dark: true,
        // Mirrors src/styles/tokens.css; components themselves use the CSS tokens.
        colors: {
          background: '#1B1E26',
          surface: '#171A21',
          primary: '#40A9FF',
          error: '#FF4D4F',
          warning: '#FFC53D',
          success: '#73D13D',
        },
      },
    },
  },
  // SVG icon set: no icon font is loaded, nothing is fetched. The app draws its icons as inline SVG.
  icons: { defaultSet: 'mdi', aliases, sets: { mdi } },
  defaults: {
    global: { ripple: false, elevation: 0 },
  },
})
