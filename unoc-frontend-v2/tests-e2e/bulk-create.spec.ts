import { test, expect } from '@playwright/test'

// Minimal happy-path: open preview server, ensure palette visible, open bulk modal, set count 5, create
// Note: Assumes backend dev server is not required for static preview; this checks only the modal behavior/UI wiring.

test('bulk create modal opens and validates', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByRole('heading', { name: 'Devices' })).toBeVisible()

    // Open bulk modal via contextmenu on a palette item (e.g., ONT)
    const ontPill = page.locator('[data-type="ONT"]').first()
    await ontPill.click({ button: 'right' })

    // Modal should appear
    const dialog = page.getByRole('dialog')
    await expect(dialog).toBeVisible()
    await expect(dialog.getByRole('heading', { level: 3 })).toContainText('Bulk Create')

    const countInput = page.locator('input[type="number"]')
    await expect(countInput).toBeFocused()
    await countInput.fill('5')

    // Primary button should exist and be enabled
    const createBtn = page.locator('[data-primary]')
    await expect(createBtn).toBeEnabled()
})
