import { expect, test } from '@playwright/test'

// Add one entry per page as routing lands (M6). Today the app renders only Overview.
const pages = [{ path: '/', heading: 'Overview' }]

for (const { path, heading } of pages) {
  test(`page ${path} loads without console errors`, async ({ page }) => {
    const errors: string[] = []
    page.on('pageerror', (err) => errors.push(err.message))
    page.on('console', (msg) => {
      if (msg.type() === 'error') errors.push(msg.text())
    })

    await page.goto(path)
    await expect(page.getByRole('heading', { name: heading })).toBeVisible()
    expect(errors).toEqual([])
  })
}
