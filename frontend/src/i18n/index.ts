import i18n from 'i18next'
import LanguageDetector from 'i18next-browser-languagedetector'
import { initReactI18next } from 'react-i18next'

import es from './locales/es.json'
import en from './locales/en.json'
import ru from './locales/ru.json'

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      es: { translation: es },
      en: { translation: en },
      ru: { translation: ru },
    },
    fallbackLng: 'es',
    supportedLngs: ['es', 'en', 'ru'],
    interpolation: { escapeValue: false },
    detection: {
      order: ['localStorage', 'navigator'],
      caches: ['localStorage'],
      lookupLocalStorage: 'spectra-lang',
    },
  })

export default i18n
