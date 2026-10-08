import en from './en.json'
import ru from './ru.json'
import uz from './uz.json'

export type Locale = 'en' | 'uz' | 'ru'
export type MessageKey = keyof typeof en

const messages: Record<Locale, Record<MessageKey, string>> = { en, uz, ru }

export function t(key: MessageKey, locale: Locale = 'en'): string {
  return messages[locale][key]
}
