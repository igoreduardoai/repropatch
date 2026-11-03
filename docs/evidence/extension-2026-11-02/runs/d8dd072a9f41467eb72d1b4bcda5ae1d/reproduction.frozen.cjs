module.exports = async (page, assert) => {
  await page.locator('#tick').click()
  const before = await page.evaluate(() => window.getRecomputes())
  assert.ok(before >= 1)
  await page.locator('#close').click()
  const atClose = await page.evaluate(() => window.getRecomputes())
  await page.locator('#tick').click()
  await page.locator('#tick').click()
  const after = await page.evaluate(() => window.getRecomputes())
  assert.equal(after, atClose, `recomputes increased after removal: ${atClose} -> ${after}`)
  // explicit derive still works
  const deriveWorks = await page.evaluate(async () => {
    const s = window.van.state(1)
    const d = window.van.derive(() => s.val * 2)
    s.val = 21; await new Promise(r => setTimeout(r, 30))
    return d.val
  })
  assert.equal(deriveWorks, 42)
}
