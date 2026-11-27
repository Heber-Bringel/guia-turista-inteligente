import '@testing-library/jest-dom/vitest'
import { afterEach } from 'vitest'
import { cleanup } from '@testing-library/react'
import { resetLanguageFromStorage } from '../i18n/language'

afterEach(() => {
  cleanup()
  localStorage.clear()
  resetLanguageFromStorage()
})
