import { describe, it, expect } from 'vitest'
// Import the component source directly as raw text to avoid any Node fs / ESM interop issues
// Vite's ?raw suffix returns the file contents as a string.
// Relative path: from this test (src/logic/__tests__) up to src/, then into components/layout.
import paletteSource from '../../components/layout/DevicePalette.vue?raw'

describe('DevicePalette types list', () => {
    it('contains extended types (ODF, NVT, BUSINESS_ONT, AON_SWITCH, AON_CPE)', () => {
        const tokens = ['BUSINESS_ONT', 'ODF', 'NVT', 'AON_SWITCH', 'AON_CPE']
        for (const token of tokens) {
            expect(paletteSource).toContain(token)
        }
    })
})
