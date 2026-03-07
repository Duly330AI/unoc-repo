import { test, expect } from '@playwright/test'

test('canvas context menu opens on right-click and closes on ESC', async ({ page }) => {
    await page.goto('/')

    // Wait for canvas to be present
    const canvas = page.locator('svg.topology-canvas')
    await expect(canvas).toBeVisible()

    // Open context menu with right-click on background
    await canvas.click({ button: 'right', position: { x: 120, y: 120 } })

    const menu = page.locator('ul.ctx')
    await expect(menu).toBeVisible()
    await expect(menu.locator('li', { hasText: 'Auto Layout (unpinned)' })).toBeVisible()

    // Close with Escape
    await page.keyboard.press('Escape')
    await expect(menu).toHaveCount(0)
})
