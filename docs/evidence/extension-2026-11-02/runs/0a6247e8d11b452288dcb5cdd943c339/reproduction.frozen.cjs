module.exports = async (page, assert) => {
  assert.equal(await page.locator('#greeting').textContent(), 'Hi Ada!')
  await page.locator('#formal').click()
  await page.waitForFunction(() => document.querySelector('#greeting').textContent === 'Good evening, Ms. Lovelace.')
  assert.equal(await page.locator('#greeting').textContent(), 'Good evening, Ms. Lovelace.')
  const r = await page.evaluate(() => {
    const card = window.vanX.reactive({greet: () => 'Hi Ada!', n: 1})
    const a = typeof card.greet === 'function' && card.greet()
    card.greet = () => 'Good evening, Ms. Lovelace.'
    return [a, card.greet(), card.n]
  })
  assert.deepEqual(r, ['Hi Ada!', 'Good evening, Ms. Lovelace.', 1])
}
