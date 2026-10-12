import { describe, expect, it } from 'vitest'
import { t } from '.'
import en from './en.json'
import ru from './ru.json'
import uz from './uz.json'

describe('i18n', () => {
  it('has the same keys in every locale', () => {
    const keys = Object.keys(en).sort()

    expect(Object.keys(uz).sort()).toEqual(keys)
    expect(Object.keys(ru).sort()).toEqual(keys)
  })

  it('defaults to English', () => {
    expect(t('app.title')).toBe('Scribbly')
  })

  it.each([
    ['uz', uz],
    ['ru', ru],
  ] as const)('uses the requested %s locale', (locale, messages) => {
    expect(t('app.tagline', locale)).toBe(messages['app.tagline'])
    expect(t('app.tagline', locale)).not.toBe(en['app.tagline'])
  })
})
