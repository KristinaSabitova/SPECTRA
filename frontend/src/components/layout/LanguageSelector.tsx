import { useTranslation } from 'react-i18next'

const LANGUAGES = [
  { code: 'es', flag: '🇪🇸' },
  { code: 'en', flag: '🇬🇧' },
  { code: 'ru', flag: '🇷🇺' },
] as const

interface Props {
  variant?: 'topbar' | 'login'
}

export default function LanguageSelector({ variant = 'topbar' }: Props) {
  const { i18n, t } = useTranslation()
  const current = i18n.language.split('-')[0]

  return (
    <div className={`lang-selector ${variant === 'login' ? 'variant-login' : ''}`}>
      {LANGUAGES.map(({ code, flag }) => (
        <button
          key={code}
          className={`lang-btn ${current === code ? 'active' : ''}`}
          onClick={() => i18n.changeLanguage(code)}
          title={t(`language.${code}`)}
        >
          <span>{flag}</span>
          <span>{t(`language.${code}`)}</span>
        </button>
      ))}
    </div>
  )
}
