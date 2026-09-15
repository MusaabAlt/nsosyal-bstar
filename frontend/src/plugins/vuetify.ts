import { createVuetify } from 'vuetify'
import { aliases, mdi } from 'vuetify/iconsets/mdi-svg'

/*
 * Vuetify supplies behaviour (application layout, buttons, tables, progress);
 * docs/UI/design-system.md supplies every visual decision. The defaults below
 * switch off the Material look the design system forbids: ripples, elevation
 * shadows, pill shapes and uppercase text (prohibitions 1, 5, 6).
 */
export const vuetify = createVuetify({
  theme: {
    defaultTheme: 'nsosyal',
    // Colour variations (lighten/darken) would invent colours outside 2.1.
    variations: false,
    themes: {
      nsosyal: {
        dark: true,
        // Mirrors src/styles/tokens.css; components themselves use the CSS tokens.
        colors: {
          background: '#1B1E26',
          surface: '#171A21',
          primary: '#324BFF',
          secondary: '#A7AAB2',
          error: '#FF4D4F',
          warning: '#F5A623',
          success: '#52C41A',
          info: '#A7AAB2',
          'on-background': '#DBDBDC',
          'on-surface': '#DBDBDC',
          'on-primary': '#FFFFFF',
        },
      },
    },
  },
  // SVG icon set: no icon font is loaded, nothing is fetched (9.2). The app
  // itself draws its few icons as inline SVG and never uses Vuetify icons.
  icons: { defaultSet: 'mdi', aliases, sets: { mdi } },
  defaults: {
    global: { ripple: false, elevation: 0 },
    VBtn: { variant: 'flat', rounded: 0, elevation: 0, ripple: false },
    VTable: { density: 'default' },
    VProgressLinear: { rounded: false, height: 2 },
  },
})
