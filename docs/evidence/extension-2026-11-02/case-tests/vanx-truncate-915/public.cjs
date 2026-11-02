module.exports = async (page, assert) => {
  assert.equal(await page.locator('#list li').count(), 5)
  await page.click('#add'); await page.waitForTimeout(50)
  assert.equal(await page.locator('#list li').count(), 6)
  assert.equal(await page.locator('#list li').last().textContent(), 'Tea')
  const popped = await page.evaluate(async () => { const v = window.items.pop(); await Promise.resolve(); return v })
  await page.waitForTimeout(50)
  assert.equal(popped, 'Tea')
  assert.equal(await page.locator('#list li').count(), 5)
}
