import { createI18n } from 'vue-i18n'
import esES from './locales/es-ES.json'

// Catalá llega cuando el hospital priorice ca-ES (post-MVP).
// Estructura preparada: añadir locales/ca-ES.json + cargarlo aquí.
export const i18n = createI18n({
  legacy: false,
  locale: 'es-ES',
  fallbackLocale: 'es-ES',
  messages: { 'es-ES': esES },
})
