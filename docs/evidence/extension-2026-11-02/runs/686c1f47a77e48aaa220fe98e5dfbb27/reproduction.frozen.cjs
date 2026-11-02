module.exports = async (page, assert) => {
  await page.waitForTimeout(300)
  assert.equal(await page.locator('#greeting').textContent(), 'Hi Ada!')
  await page.click('#formal')
  await page.waitForTimeout(300)
  assert.equal(await page.locator('#greeting').textContent(), 'Good evening, Ms. Lovelace.')
  const r = await page.evaluate(() => [typeof window.card.greet, window.card.greet()])
  assert.deepEqual(r, ['function', 'Good evening, Ms. Lovelace.'])
}
